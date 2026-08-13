package com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes;

import com.college_advisor.service.agent.CollegeAdvisorAgent;
import com.college_advisor.service.graph.state.ErrorState.ErrorContext;
import com.college_advisor.service.graph.state.ErrorState.ErrorInfo;
import com.college_advisor.service.graph.state.PlanTask;
import com.college_advisor.service.graph.state.SubgraphState;
import com.college_advisor.service.graph.state.TaskResult;
import com.college_advisor.service.tools.CourseDataTools;
import com.college_advisor.service.tools.GraduationTools;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.service.AiServices;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.List;
import java.util.Map;

public class CoursePlannerNode implements NodeAction<SubgraphState> {

    private static final String SYSTEM_PROMPT = """
            You are a degree planner for STAT-major students at UIUC.

            Call exactly TWO tools, in this order:
            1. getGraduationRequirements() — get required courses and elective categories.
            2. findAvailableCourses(completedCourses) — get currently unlocked STAT courses.

            Do NOT call any other tools. Do not call getCourseDetails or getPrerequisiteChain.
            The database only has STAT courses — for MATH/CS requirements, use the
            graduation requirements text and state assumptions explicitly.

            After the two tool calls, immediately output the plan.
            Default: plan the next semester only unless the student asks for more.
            Output a semester-by-semester plan: each course, its role (required/elective),
            and whether prereqs are met. End with remaining requirements after the plan.
            """;

    private final CollegeAdvisorAgent agent;

    public CoursePlannerNode(ChatModel model, CourseDataTools courseData, GraduationTools graduation) {
        this.agent = AiServices.builder(CollegeAdvisorAgent.class)
                .chatModel(model)
                .tools(courseData, graduation)
                .systemMessageProvider(id -> SYSTEM_PROMPT)
                .maxSequentialToolsInvocations(15)
                .build();
    }

    public CoursePlannerNode() {
        this.agent = null;
    }

    @Override
    public Map<String, Object> apply(SubgraphState state) throws Exception {
        String taskId = state.currentTaskId();
        System.out.println("[course_planner] executing task: " + taskId);

        if (agent == null) {
            return Map.of(
                    "taskResults", List.of(List.of(new TaskResult(taskId, "CoursePlanner agent executed successfully."))),
                    "nodeHistory",  "course_planner"
            );
        }

        PlanTask task = findTask(state, taskId);
        StringBuilder input = new StringBuilder();
        input.append("Goal: ").append(task.goal());
        if (!task.constraints().isEmpty()) {
            input.append("\nConstraints: ").append(task.constraints());
        }

        List<TaskResult> prior = state.taskResults().stream()
                .flatMap(List::stream)
                .toList();
        if (!prior.isEmpty()) {
            input.append("\n\nContext from prior tasks:");
            prior.forEach(r ->
                input.append("\n[").append(r.taskId()).append("]: ").append(r.result())
            );
        }

        try {
            String result = agent.chat(input.toString());
            return Map.of(
                    "taskResults", List.of(List.of(new TaskResult(taskId, result != null ? result : ""))),
                    "nodeHistory",  "course_planner"
            );
        } catch (Exception e) {
            System.err.println("[course_planner] agent error: " + e.getMessage());
            ErrorInfo err = new ErrorInfo("course_planner", "AGENT_ERROR", e.getMessage(), false);
            return Map.of(
                    "errorContext", new ErrorContext(err, state.errorContext().nodeRetries(), "subgraph_error_handler"),
                    "nodeHistory",  "course_planner"
            );
        }
    }

    public String route(SubgraphState state) {
        if (state.currentError() != null) return "subgraph_error_handler";
        return "dispatcher";
    }

    private PlanTask findTask(SubgraphState state, String taskId) {
        return state.plan().chains().stream()
                .flatMap(List::stream)
                .filter(t -> t.id().equals(taskId))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("Task not found: " + taskId));
    }
}

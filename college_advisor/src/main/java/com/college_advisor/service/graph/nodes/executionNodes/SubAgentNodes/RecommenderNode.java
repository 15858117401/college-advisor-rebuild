package com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes;

import com.college_advisor.service.agent.ReactAgent;
import com.college_advisor.service.agent.ReactResult;
import com.college_advisor.service.graph.state.ErrorState.ErrorContext;
import com.college_advisor.service.graph.state.ErrorState.ErrorInfo;
import com.college_advisor.service.graph.state.PlanTask;
import com.college_advisor.service.graph.state.SubgraphState;
import com.college_advisor.service.graph.state.TaskResult;
import com.college_advisor.service.tools.CourseDataTools;
import com.college_advisor.service.tools.CourseSectionTools;
import com.college_advisor.service.tools.GraduationTools;
import com.college_advisor.service.tools.ProfessorRatingTools;
import com.college_advisor.service.tools.SkillTools;
import dev.langchain4j.model.chat.ChatModel;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.List;
import java.util.Map;

public class RecommenderNode implements NodeAction<SubgraphState> {

    private static final String SYSTEM_PROMPT = """
            You are a course recommender for STAT-major students at UIUC.
            Your job is preference-driven: recommend courses that best fit the student's
            interests, goals, GPA target, or workload constraints.
            You do NOT schedule classes or build timetables — focus only on WHAT to take, not WHEN.

            If prior task results are provided in the input (e.g. a degree plan produced by
            course_planner), treat them as authoritative context — respect required courses,
            prerequisite ordering, and any constraints already established.

            Use the available tools to look up course details, filter by attributes, and check
            graduation requirements so you know which courses are required vs elective.

            **Skill loading rule (CRITICAL) — think through these steps before any tool call:**
            Step 1 — Read the student's goal and constraints carefully.
            Step 2 — Reason: does this goal signal any of the following scenarios?
              - minimal_graduation: easy graduation, light workload, low effort, no attendance,
                online classes, afternoon sections, minimal, stress-free, chill semester
              - grad_school_prep: grad school, PhD, master's program, research, doctoral,
                academic rigor, strong transcript, graduate application
            Step 3 — Decide:
              - If YES: call load_skill as your VERY FIRST tool call, before anything else.
                Choose exactly one skill name that best matches the goal.
              - If NO: skip load_skill entirely and proceed directly to other tools.
            Step 4 — After this one-time decision, NEVER call load_skill again.
                      This rule has no exceptions.

            Output a ranked list of specific course codes with a one-sentence justification for each.
            """;

    private final ReactAgent reactAgent;

    public RecommenderNode(ChatModel model,
                           CourseDataTools courseData,
                           CourseSectionTools sections,
                           GraduationTools graduation,
                           ProfessorRatingTools profRating,
                           SkillTools skill) {
        this.reactAgent = new ReactAgent(model, SYSTEM_PROMPT, 20,
                new Object[]{courseData, sections, graduation, profRating, skill});
    }

    public RecommenderNode() {
        this.reactAgent = null;
    }

    @Override
    public Map<String, Object> apply(SubgraphState state) throws Exception {
        String taskId = state.currentTaskId();
        System.out.println("[recommender] executing task: " + taskId);

        if (reactAgent == null) {
            return Map.of(
                    "taskResults", List.of(List.of(new TaskResult(taskId, "Recommender agent executed successfully."))),
                    "nodeHistory", "recommender"
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

        ReactResult result = reactAgent.run(input.toString());
        if (!result.success()) {
            ErrorInfo err = new ErrorInfo("recommender", "AGENT_ERROR", result.error(), result.retryable());
            return Map.of(
                    "errorContext", new ErrorContext(err, state.errorContext().nodeRetries(), "subgraph_error_handler"),
                    "nodeHistory",  "recommender"
            );
        }
        return Map.of(
                "taskResults", List.of(List.of(new TaskResult(taskId, result.content()))),
                "nodeHistory",  "recommender"
        );
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

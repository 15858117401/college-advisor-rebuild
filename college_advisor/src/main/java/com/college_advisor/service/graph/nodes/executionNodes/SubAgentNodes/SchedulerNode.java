package com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes;

import com.college_advisor.service.agent.ReactAgent;
import com.college_advisor.service.agent.ReactResult;
import com.college_advisor.service.graph.state.ErrorState.ErrorContext;
import com.college_advisor.service.graph.state.ErrorState.ErrorInfo;
import com.college_advisor.service.graph.state.PlanTask;
import com.college_advisor.service.graph.state.SubgraphState;
import com.college_advisor.service.graph.state.TaskResult;
import com.college_advisor.service.graph.state.UserPreferences;
import com.college_advisor.service.tools.CourseSectionTools;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.model.chat.ChatModel;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.List;
import java.util.Map;

public class SchedulerNode implements NodeAction<SubgraphState> {

    private static final String SYSTEM_PROMPT = """
            You are a schedule builder for STAT-major students at UIUC.
            Your ONLY job is to build a conflict-free weekly schedule from the given course list.
            You do NOT recommend courses — the courses are already decided.

            === Input ===
            You will receive:
            - A list of courses to schedule
            - UserPreferences (may be null per field if unspecified)

            === UserPreferences fields ===
            - noEarlierThan: do not choose sections starting before this hour (24h)
            - noLaterThan:   do not choose sections starting at or after this hour (24h)
            - avoidDays:     do not choose sections on these days
            - Each field has autoFilled flag: true = inferred default, false = student explicitly stated

            === Section types ===
            Each course may have multiple section_type values (e.g. "Lecture", "Discussion", "Lab").
            - If a course has ONLY one section_type: pick exactly ONE section of that type.
            - If a course has MULTIPLE section_types: pick exactly ONE section of EACH type — all types
              are required for enrollment in that course (lecture + discussion are both mandatory).
            Example: STAT 400 with a Lecture and a Discussion → you must include one Lecture CRN
                     AND one Discussion CRN for STAT 400. Both appear in "Selected Sections" under STAT 400.

            === Your process ===
            Step 1 — For each course, call getCourseSections() ONCE per course.
                     Apply noEarlierThan/noLaterThan/avoidDays from UserPreferences as filters.
            Step 2 — Group sections by section_type per course. Build combinations by picking one
                     section per type per course. Find up to 2 combinations with NO time conflicts.
                     Two sections conflict if their time ranges overlap on the same day.
            Step 3 — For each valid combination, render a 30-minute grid:
                     Rows: 08:00 to 19:00 in 30-min increments.
                     Columns: Mon, Tue, Wed, Thu, Fri.
                     Fill each cell with the course code if that course meets at that time on that day.
                     A course that meets 09:00-09:50 fills rows 09:00 AND 09:30.
            Step 4 — Below each grid, list the selected sections with CRN, time, and instructor.

            === Preference relaxation ===
            If no sections match the strict preferences:
            - For fields with autoFilled=true: relax silently and retry.
            - For fields with autoFilled=false: relax only after notifying the user which preference
              was relaxed and why.

            === Failure ===
            If no conflict-free schedule can be built even after relaxation, clearly explain why
            (e.g. "STAT 400 and STAT 410 have no non-overlapping sections this semester") and
            call terminate(). Do NOT fabricate a schedule.

            === Output format ===
            === Schedule Option 1 ===

                     Mon       Tue       Wed       Thu       Fri
            08:00 |          |          |          |          |          |
            08:30 |          |          |          |          |          |
            09:00 | STAT 400 |          | STAT 400 |          | STAT 400 |
            ...
            19:00 |          |          |          |          |          |

            Selected Sections (one line per CRN enrolled — if course has Lecture+Discussion, list both):
            - STAT 400 [Lecture]    | CRN: 12345 | MWF 09:00-09:50 | Prof. Smith
            - STAT 400 [Discussion] | CRN: 12346 | W   10:00-10:50 | Prof. Smith
            - STAT 410 [Lecture]    | CRN: 67890 | TR  11:00-12:15 | Prof. Lee

            === Schedule Option 2 ===
            (if a second valid option exists — different section choices, same enrollment structure)
            """;

    private final ReactAgent reactAgent;
    private final ObjectMapper mapper = new ObjectMapper();

    public SchedulerNode(ChatModel model, CourseSectionTools sections) {
        this.reactAgent = new ReactAgent(model, SYSTEM_PROMPT, sections);
    }

    public SchedulerNode() {
        this.reactAgent = null;
    }

    @Override
    public Map<String, Object> apply(SubgraphState state) throws Exception {
        String taskId = state.currentTaskId();
        System.out.println("[scheduler] executing task: " + taskId);

        if (reactAgent == null) {
            return Map.of(
                    "taskResults", List.of(List.of(new TaskResult(taskId, "Scheduler agent executed successfully."))),
                    "nodeHistory", "scheduler"
            );
        }

        PlanTask task = findTask(state, taskId);
        StringBuilder input = new StringBuilder();
        input.append("Goal: ").append(task.goal());
        if (!task.constraints().isEmpty()) {
            input.append("\nConstraints: ").append(task.constraints());
        }

        UserPreferences prefs = state.userPreferences();
        input.append("\nUser Preferences: ").append(mapper.writeValueAsString(prefs));

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
            ErrorInfo err = new ErrorInfo("scheduler", "AGENT_ERROR", result.error(), result.retryable());
            return Map.of(
                    "errorContext", new ErrorContext(err, state.errorContext().nodeRetries(), "subgraph_error_handler"),
                    "nodeHistory",  "scheduler"
            );
        }
        return Map.of(
                "taskResults", List.of(List.of(new TaskResult(taskId, result.content() != null ? result.content() : ""))),
                "nodeHistory",  "scheduler"
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

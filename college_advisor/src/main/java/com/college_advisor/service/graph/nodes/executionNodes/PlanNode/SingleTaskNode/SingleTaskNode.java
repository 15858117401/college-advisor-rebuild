package com.college_advisor.service.graph.nodes.executionNodes.PlanNode.SingleTaskNode;

import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.graph.state.Plan;
import com.college_advisor.service.graph.state.PlanTask;
import com.college_advisor.service.graph.state.PreferenceField;
import com.college_advisor.service.graph.state.UserPreferences;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.data.message.SystemMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.request.ChatRequest;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class SingleTaskNode implements NodeAction<MainState> {

    private static final String PREFERENCE_PROMPT = """
            Extract student scheduling preferences from the input. Output ONLY valid JSON, no explanation.

            Fields (all nullable — use null if not mentioned or cannot be reasonably inferred):
            {
              "noEarlierThan":         <integer 0-23 or null>,
              "noEarlierThanAuto":     <true if inferred default, false if explicitly stated>,
              "noLaterThan":           <integer 0-23 or null>,
              "noLaterThanAuto":       <true if inferred default, false if explicitly stated>,
              "avoidDays":             <["Mon","Tue","Wed","Thu","Fri"] subset or null>,
              "avoidDaysAuto":         <true/false>,
              "noMandatoryAttendance": <true/false or null>,
              "noMandatoryAuto":       <true/false>,
              "workload":              <"light"|"medium"|"heavy" or null>,
              "workloadAuto":          <true/false>,
              "difficulty":            <"Easy"|"Medium"|"Hard" or null>,
              "difficultyAuto":        <true/false>,
              "minGpa":                <decimal or null>,
              "minGpaAuto":            <true/false>
            }

            Rules:
            - Set autoFilled=false only when the student explicitly stated the preference.
            - Set autoFilled=true when you infer a reasonable default (e.g. student said nothing about time → noEarlierThan=9, autoFilled=true).
            - If a dimension truly cannot be inferred, leave both value and auto as null/false.
            """;

    private static final String SYSTEM_PROMPT = """
            You are a task planner for a college advising system.
            Given a student request, produce a JSON plan with EXACTLY ONE task.
            Output ONLY valid JSON — no markdown fences, no explanation.

            Available task types:
            - "recommender"    : recommend courses based on interests, background, or GPA
            - "scheduler"      : build a conflict-free schedule given specific courses or time constraints
            - "course_planner" : map out a single or multi-semester degree plan to meet graduation requirements

            Output format:

              "id": "t1",
              "taskType": "<recommender|scheduler|course_planner>",
              "goal": "<one specific actionable sentence>",
              "constraints": ["<constraint>"]


            Rules:
            - "goal" must be specific and actionable, derived directly from the student's request.
            - "constraints" captures hard limits or filters (can be empty []).
            """;

    private final ChatModel model;
    private final ObjectMapper mapper = new ObjectMapper();

    public SingleTaskNode(ChatModel model) {
        this.model = model;
    }

    public SingleTaskNode() {
        this(null);
    }

    @Override
    public Map<String, Object> apply(MainState state) throws Exception {
        System.out.println("[build_single_plan] executing");

        if (model == null) {
            Plan stub = new Plan(List.of(List.of(new PlanTask(
                    "t1", "recommender", state.userInput(), List.of()))));
            return Map.of("taskContext", state.taskContext().withPlan(stub), "nodeHistory", "build_single_plan");
        }

        var response = model.chat(ChatRequest.builder()
                .messages(List.of(
                        SystemMessage.from(SYSTEM_PROMPT),
                        UserMessage.from(buildContextualInput(state.userInput(), state.conversationSummary()))))
                .build());

        Plan plan = parsePlan(response.aiMessage().text(), state.userInput());
        System.out.println("[build_single_plan] plan: " + mapper.writeValueAsString(plan));

        UserPreferences prefs = extractPreferences(state.userInput());
        System.out.println("[build_single_plan] preferences: " + mapper.writeValueAsString(prefs));

        return Map.of(
                "taskContext",    state.taskContext().withPlan(plan),
                "userPreferences", prefs,
                "nodeHistory",    "build_single_plan"
        );
    }

    public String route(MainState state) throws Exception {
        if (state.currentError() != null) return "error_handler";
        return "execution_subgraph";
    }

    private static String buildContextualInput(String userInput, String summary) {
        if (summary == null || summary.isEmpty()) return userInput;
        return "Conversation history:\n" + summary + "\n\nCurrent request: " + userInput;
    }

    private UserPreferences extractPreferences(String userInput) {
        try {
            var prefResponse = model.chat(ChatRequest.builder()
                    .messages(List.of(
                            SystemMessage.from(PREFERENCE_PROMPT),
                            UserMessage.from(userInput)))
                    .build());
            return parsePreferences(stripFences(prefResponse.aiMessage().text()));
        } catch (Exception e) {
            System.err.println("[build_single_plan] preference extraction failed: " + e.getMessage());
            return UserPreferences.empty();
        }
    }

    private UserPreferences parsePreferences(String json) {
        try {
            JsonNode n = mapper.readTree(json);
            return new UserPreferences(
                    fieldInt(n, "noEarlierThan", "noEarlierThanAuto"),
                    fieldInt(n, "noLaterThan",   "noLaterThanAuto"),
                    fieldDays(n, "avoidDays",    "avoidDaysAuto"),
                    fieldBool(n, "noMandatoryAttendance", "noMandatoryAuto"),
                    fieldStr(n,  "workload",      "workloadAuto"),
                    fieldStr(n,  "difficulty",    "difficultyAuto"),
                    fieldDbl(n,  "minGpa",        "minGpaAuto")
            );
        } catch (Exception e) {
            System.err.println("[build_single_plan] preference JSON parse failed: " + e.getMessage());
            return UserPreferences.empty();
        }
    }

    private PreferenceField<Integer> fieldInt(JsonNode n, String val, String auto) {
        JsonNode v = n.get(val);
        if (v == null || v.isNull()) return null;
        return new PreferenceField<>(v.asInt(), n.path(auto).asBoolean(true));
    }

    private PreferenceField<Double> fieldDbl(JsonNode n, String val, String auto) {
        JsonNode v = n.get(val);
        if (v == null || v.isNull()) return null;
        return new PreferenceField<>(v.asDouble(), n.path(auto).asBoolean(true));
    }

    private PreferenceField<String> fieldStr(JsonNode n, String val, String auto) {
        JsonNode v = n.get(val);
        if (v == null || v.isNull()) return null;
        return new PreferenceField<>(v.asText(), n.path(auto).asBoolean(true));
    }

    private PreferenceField<Boolean> fieldBool(JsonNode n, String val, String auto) {
        JsonNode v = n.get(val);
        if (v == null || v.isNull()) return null;
        return new PreferenceField<>(v.asBoolean(), n.path(auto).asBoolean(true));
    }

    private PreferenceField<List<String>> fieldDays(JsonNode n, String val, String auto) {
        JsonNode v = n.get(val);
        if (v == null || v.isNull()) return null;
        List<String> days = new ArrayList<>();
        v.forEach(d -> days.add(d.asText()));
        return new PreferenceField<>(days, n.path(auto).asBoolean(true));
    }

    private Plan parsePlan(String text, String fallbackUserInput) {
        try {
            String cleaned = stripFences(text);
            PlanTask task = mapper.readValue(cleaned, PlanTask.class);
            return new Plan(List.of(List.of(task)));
        } catch (Exception e) {
            System.err.println("[build_single_plan] failed to parse task JSON, using fallback: " + e.getMessage());
            return new Plan(List.of(List.of(new PlanTask(
                    "t1", "recommender", fallbackUserInput, List.of()))));
        }
    }

    private static String stripFences(String text) {
        if (text == null) return "{}";
        String s = text.strip();
        if (s.startsWith("```")) {
            int start = s.indexOf('\n');
            int end   = s.lastIndexOf("```");
            if (start >= 0 && end > start) return s.substring(start + 1, end).strip();
        }
        return s;
    }
}

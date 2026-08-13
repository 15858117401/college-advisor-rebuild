package com.college_advisor.service.graph.client;

import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.openai.OpenAiChatModel;

import java.util.List;
import java.util.Set;

public class RouterClient {

    private static final Set<String> VALID_ROUTES =
            Set.of("clarify", "simple_task", "build_single_plan", "planner");

    private final ChatModel model;

    public RouterClient(String apiKey, String modelName) {
        this.model = OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(apiKey)
                .modelName(modelName)
                .temperature(0.0)
                .maxTokens(800)
                .build();
    }

    /** Observability overload — used by eval tests to inject a shared listener. */
    public RouterClient(String apiKey, String modelName, List<ChatModelListener> listeners) {
        this.model = OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(apiKey)
                .modelName(modelName)
                .temperature(0.0)
                .maxTokens(800)
                .listeners(listeners)
                .build();
    }

    /**
     * Classifies userInput into one of: clarify, simple_task, build_single_plan, planner.
     * Falls back to "simple_task" on any error.
     */
    public String classify(String userInput) {
        return classify(userInput, "");
    }

    public String classify(String userInput, String summary) {
        try {
            String response = model.chat(buildPrompt(userInput, summary));
            return parseRoute(response);
        } catch (Exception e) {
            System.err.println("[RouterClient] classification failed, defaulting to simple_task: " + e.getMessage());
            return "simple_task";
        }
    }

    private String buildPrompt(String userInput, String summary) {
        String rules = """
                You are a router for a STAT-major advising assistant at UIUC.
                The student message may be in any language.

                If CONVERSATION HISTORY is provided, use it to resolve references
                (e.g. "that course", "it", "those courses") before routing.
                A follow-up like "Who teaches that course?" after discussing STAT 400
                should be treated as "Who teaches STAT 400?" and routed to simple_task.

                Think step by step, then write exactly one final line:
                Category: <clarify|simple_task|build_single_plan|planner>

                ════════════════════════════════════════════════════
                ROUTE DEFINITIONS  (check in order; first match wins)
                ════════════════════════════════════════════════════

                1. clarify
                   Purpose : Ask for more info before acting.
                   Use when :
                     • Off-topic, empty, or nonsense (greetings, trivia, arithmetic)
                     • Too vague to retrieve anything ("help me", "I have a question")
                     • Personalized request with MISSING critical context:
                         - No completed courses → "What should I take next?"
                         - No year/goal → "Recommend me courses" / "Build my schedule"
                         - GPA target but no current GPA or credit count given
                   Do NOT use if the question is answerable from the course catalog
                              without knowing who the student is.
                   Do NOT use if the last assistant message in history was a clarifying question
                              and the user is now answering it — route to the appropriate execution node instead.

                2. simple_task
                   Purpose : Look up data from the course catalog — no plan generated.
                   Use when :
                     • Course info  (credits, difficulty, avg GPA, workload, attendance)
                     • Prerequisite lookup — forward ("need before X") or reverse ("after X")
                     • Section details  (times, CRN, instructor, location)
                     • Course filtering  (by difficulty / GPA / workload / attendance)
                     • Semantic search  ("any courses about machine learning?")
                     • Instructor queries  ("who teaches X" / "what does Prof Y teach")
                     • Professor reputation via Reddit or Rate My Professor
                     • Comparing named courses on objective attributes
                     • Graduation requirement text
                   Do NOT use if the student asks to BUILD / ARRANGE / CREATE a schedule or plan.

                3. build_single_plan
                   Purpose : Generate one personalized advising plan.
                   Use when : Exactly ONE goal (course recommendation / schedule build /
                              degree plan / GPA target) AND the message contains enough
                              context to act on — year, STAT major, and completed courses
                              can be present anywhere in the message (explicit or implied);
                              they do not need to be a formal declaration this turn.
                   Do NOT use if :
                     • Key context is absent from the message (no courses mentioned, no year,
                       no goal) → use clarify instead
                     • Two or more separable goals are stacked → use planner instead

                4. planner
                   Purpose : Coordinate two or more separate advising outcomes.
                   Use when : Goals are chained or bundled ("recommend courses AND
                              build my schedule", "pick electives AND map my degree").
                   Do NOT use if : "after finishing X, what can I take?" — that is a
                              prerequisite-sequence question, not stacked goals → simple_task.

                ════════════════════════════════════════════════════
                EXAMPLES
                ════════════════════════════════════════════════════
                clarify        "What should I take next?"
                clarify        "I am a junior in STAT, recommend me something"  ← no completed courses
                simple_task    "Which STAT courses are low difficulty?"
                simple_task    "What do people say about Professor Smith on Reddit?"
                build_single_plan  "I am a junior in STAT, done STAT 200 + STAT 400, recommend next semester courses"
                planner        "Recommend me courses, then build me a schedule"

                ════════════════════════════════════════════════════
                """;
        StringBuilder prompt = new StringBuilder(rules);
        if (!summary.isEmpty()) {
            prompt.append("CONVERSATION HISTORY\n").append(summary).append("\n\n");
        }
        prompt.append("QUERY\n\"").append(userInput).append("\"");
        return prompt.toString();
    }

    private String parseRoute(String responseText) {
        String raw = responseText.toLowerCase();

        // CoT output looks like "reasoning: ...\ncategory: simple_task"
        // Extract the value after the last "category:" occurrence
        String category = raw;
        int idx = raw.lastIndexOf("category:");
        if (idx >= 0) {
            category = raw.substring(idx + "category:".length()).strip();
            // take only the first word (ignore anything after whitespace/punctuation)
            category = category.split("[\\s,\\.]")[0].strip();
        } else {
            // fallback: model returned bare word — take first token
            category = raw.strip().split("\\s+")[0];
        }

        // The model returns "composite_task"; map it to the graph node name "planner"
        if (category.equals("composite_task")) return "planner";

        return VALID_ROUTES.contains(category) ? category : "simple_task";
    }
}

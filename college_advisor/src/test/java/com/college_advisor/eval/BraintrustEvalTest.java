package com.college_advisor.eval;

import com.college_advisor.eval.braintrust.BraintrustEvent;
import com.college_advisor.eval.braintrust.BraintrustLogger;
import com.college_advisor.eval.listener.LlmCallEvent;
import com.college_advisor.eval.listener.LlmEventListener;
import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.graph.state.Plan;
import com.college_advisor.service.graph.state.PlanTask;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.tools.*;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.InputStream;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Stream;

/**
 * Braintrust eval — cases categorized by route, each case runs concurrently.
 * Each @ParameterizedTest invocation creates its own listener+model+graph
 * so per-case token counts are fully isolated even under parallel execution.
 *
 * Run one category:     ./mvnw test -Dtest="BraintrustEvalTest#runSimpleTask"
 * Run all (concurrent): ./mvnw test -Dtest=BraintrustEvalTest
 */
class BraintrustEvalTest {

    private static final String PROJECT_NAME = "college_advisor";
    private static final DateTimeFormatter FMT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH-mm-ss").withZone(ZoneOffset.UTC);

    // ── Input sets by route ───────────────────────────────────────────────────

    static Stream<String> simpleTaskInputs() {
        return Stream.of(
                "What is STAT 432?",
                "What are the prerequisites for STAT 425?",
                "Which STAT courses teach Python?",
                "Who teaches STAT 432?",
                "Which courses list STAT 400 as a prerequisite?",
                "What is the average GPA in STAT 410?",
                "Are there any STAT courses related to probability theory?"
        );
    }

    static Stream<String> clarifyInputs() {
        return Stream.of(
                "Help me choose courses",
                "I am a junior in the STAT major. What should I take next?",
                "What should I take this semester?",
                "Help me plan my degree"
        );
    }

    static Stream<String> buildSinglePlanInputs() {
        return Stream.of(
                "I am a sophomore in the STAT major and I have completed STAT 100 and STAT 200. Recommend me 3 courses for next semester.",
                "I want to study data science. I am a junior in the STAT major and have already taken STAT 107 and STAT 200. Recommend me some courses.",
                "I am a junior in the STAT major and I want to take STAT 400 and STAT 432 next semester. Help me build a schedule that avoids Friday classes.",
                "I am a junior in the STAT major and have completed STAT 100, STAT 200, STAT 400, and STAT 410. Help me plan my remaining semesters to graduate on time."
        );
    }

    static Stream<String> plannerInputs() {
        return Stream.of(
                "I am a sophomore in the STAT major and have completed STAT 100 and STAT 107. Recommend me courses for next semester, then build me a schedule around them.",
                "I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. I still need 2 electives — recommend them and then build me a schedule for next semester.",
                "I am a sophomore in the STAT major and have completed STAT 107 and STAT 200. Recommend what I should take next semester and also map out the rest of my degree."
        );
    }

    // ── Shared infrastructure (stateless / thread-safe) ───────────────────────

    private static String           dashApiKey;
    private static String           modelName;
    private static String           embeddingModel;
    private static String           tavilyApiKey;
    private static HikariDataSource dataSource;
    private static CourseDataTools  courseData;
    private static CourseSectionTools sections;
    private static GraduationTools  graduation;
    private static ProfessorRatingTools profRating;
    private static SkillTools       skill;
    private static BraintrustLogger braintrust;
    private static String           experimentId;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = BraintrustEvalTest.class.getClassLoader()
                .getResourceAsStream("application-local.properties")) {
            props.load(in);
        }

        dashApiKey    = props.getProperty("dashscope.api-key");
        modelName     = props.getProperty("dashscope.model-name");
        embeddingModel = props.getProperty("dashscope.embedding-model-name");
        tavilyApiKey  = props.getProperty("tavily.api-key");
        String braintrustKey = props.getProperty("braintrust.api-key");

        HikariConfig hikari = new HikariConfig();
        hikari.setJdbcUrl(props.getProperty("spring.datasource.url"));
        hikari.setUsername(props.getProperty("spring.datasource.username").strip());
        hikari.setPassword(props.getProperty("spring.datasource.password").strip());
        hikari.setMaximumPoolSize(20);
        dataSource = new HikariDataSource(hikari);

        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        EmbeddingClient embeddingClient = new EmbeddingClient(dashApiKey, embeddingModel, 768);
        TavilyClient tavily = new TavilyClient(tavilyApiKey);

        courseData  = new CourseDataTools(jdbc, embeddingClient);
        sections    = new CourseSectionTools(jdbc);
        graduation  = new GraduationTools(jdbc);
        profRating  = new ProfessorRatingTools(tavily);
        skill       = new SkillTools(jdbc);

        braintrust = new BraintrustLogger(braintrustKey);
        String experimentName = PROJECT_NAME + "-" + FMT.format(Instant.now());
        experimentId = braintrust.createExperiment(PROJECT_NAME, experimentName);
        System.out.println("[BraintrustEvalTest] experiment: " + experimentName + " id=" + experimentId);
    }

    @AfterAll
    static void tearDown() {
        if (dataSource != null) dataSource.close();
    }

    // ── Per-category parameterized tests ──────────────────────────────────────
    // junit-platform.properties sets mode.default=concurrent, so each
    // parameterized invocation runs in parallel. Each case creates its own
    // listener + model + graph to avoid shared-state races.

    @ParameterizedTest(name = "[simple_task] {0}")
    @MethodSource("simpleTaskInputs")
    void runSimpleTask(String input) throws Exception {
        runIsolated(input);
    }

    @ParameterizedTest(name = "[clarify] {0}")
    @MethodSource("clarifyInputs")
    void runClarify(String input) throws Exception {
        runIsolated(input);
    }

    @ParameterizedTest(name = "[build_single_plan] {0}")
    @MethodSource("buildSinglePlanInputs")
    void runBuildSinglePlan(String input) throws Exception {
        runIsolated(input);
    }

    @ParameterizedTest(name = "[planner] {0}")
    @MethodSource("plannerInputs")
    void runPlanner(String input) throws Exception {
        runIsolated(input);
    }

    // ── Core logic ────────────────────────────────────────────────────────────

    /** Creates per-case listener + model + router + graph — no shared mutable state. */
    private static void runIsolated(String input) throws Exception {
        LlmEventListener caseListener = new LlmEventListener();
        List<ChatModelListener> ll = List.of(caseListener);

        OpenAiChatModel chatModel = OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(dashApiKey)
                .modelName(modelName)
                .temperature(0.2)
                .listeners(ll)
                .build();

        CompiledGraph<MainState> caseGraph = ParentGraph.build(
                new RouterClient(dashApiKey, modelName, ll),
                chatModel,
                courseData, sections, graduation, profRating, skill);

        long wallStart = System.currentTimeMillis();
        MainState state;
        try {
            state = caseGraph.invoke(Map.of("userInput", input)).get();
        } catch (Exception e) {
            System.err.printf("[BraintrustEvalTest] graph.invoke failed [%s]: %s%n", input, e);
            return;
        }
        long wallLatencyMs = System.currentTimeMillis() - wallStart;

        List<LlmCallEvent> calls = caseListener.snapshot();

        List<Map<String, Object>> llmCallMaps = new ArrayList<>();
        for (LlmCallEvent call : calls) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("model",            call.modelName());
            m.put("promptTokens",     call.promptTokens());
            m.put("completionTokens", call.completionTokens());
            m.put("totalTokens",      call.totalTokens());
            m.put("latencyMs",        call.latencyMs());
            m.put("toolCalls",        call.toolCalls());
            llmCallMaps.add(m);
        }

        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("route",       state.routeDecision());
        metadata.put("nodeHistory", state.nodeHistory());
        metadata.put("plan",        serializePlan(state.plan()));
        metadata.put("llmCalls",    llmCallMaps);

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("totalLatencyMs",   wallLatencyMs);
        metrics.put("promptTokens",     caseListener.totalPromptTokens());
        metrics.put("completionTokens", caseListener.totalCompletionTokens());
        metrics.put("totalTokens",      caseListener.totalTokens());
        metrics.put("llmCallCount",     calls.size());

        braintrust.logEvent(experimentId, new BraintrustEvent(
                UUID.randomUUID().toString(),
                input,
                state.response() != null ? state.response() : "",
                metadata,
                metrics,
                List.of(state.routeDecision())));

        System.out.printf("[eval] route=%-20s | latency=%5dms | tokens=%4d (p=%4d c=%3d) | calls=%d | input=%.60s%n",
                state.routeDecision(), wallLatencyMs,
                caseListener.totalTokens(), caseListener.totalPromptTokens(),
                caseListener.totalCompletionTokens(), calls.size(), input);
    }

    private static Object serializePlan(Plan plan) {
        if (plan == null || plan.chains() == null || plan.chains().isEmpty()) return null;
        List<List<Map<String, Object>>> chains = new ArrayList<>();
        for (List<PlanTask> chain : plan.chains()) {
            List<Map<String, Object>> serializedChain = new ArrayList<>();
            for (PlanTask task : chain) {
                Map<String, Object> t = new LinkedHashMap<>();
                t.put("id",          task.id());
                t.put("taskType",    task.taskType());
                t.put("goal",        task.goal());
                t.put("constraints", task.constraints());
                serializedChain.add(t);
            }
            chains.add(serializedChain);
        }
        return chains;
    }
}

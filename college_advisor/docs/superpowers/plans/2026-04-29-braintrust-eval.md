# Braintrust Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Braintrust evaluation harness that captures token usage and latency for every LLM call across the full graph pipeline, using existing LLM test cases as the dataset.

**Architecture:** Three decoupled layers — `listener/` captures raw LLM events (no Braintrust knowledge), `braintrust/` sends data via REST (no graph knowledge), `BraintrustEvalTest` wires them together. The only production-code change is adding one constructor overload to `RouterClient`.

**Tech Stack:** langchain4j 1.13.1 `ChatModelListener`, Java 11 `HttpClient`, Jackson (already in pom.xml), Braintrust REST API.

---

## File Map

**Create (test scope):**
- `src/test/java/com/college_advisor/eval/listener/LlmCallEvent.java`
- `src/test/java/com/college_advisor/eval/listener/LlmEventListener.java`
- `src/test/java/com/college_advisor/eval/braintrust/BraintrustEvent.java`
- `src/test/java/com/college_advisor/eval/braintrust/BraintrustLogger.java`
- `src/test/java/com/college_advisor/eval/dataset/EvalCase.java`
- `src/test/java/com/college_advisor/eval/dataset/EvalDataset.java`
- `src/test/java/com/college_advisor/eval/BraintrustEvalTest.java`
- `src/test/java/com/college_advisor/eval/listener/LlmEventListenerTest.java`

**Modify (production):**
- `src/main/java/com/college_advisor/service/graph/client/RouterClient.java` — add one constructor overload
- `src/main/resources/application-local.properties` — add `braintrust.api-key`

---

## Task 1: Add Braintrust API key to config and RouterClient listener overload

**Files:**
- Modify: `src/main/resources/application-local.properties`
- Modify: `src/main/java/com/college_advisor/service/graph/client/RouterClient.java`

- [ ] **Step 1: Add key to application-local.properties**

Open `src/main/resources/application-local.properties` and append:
```properties
braintrust.api-key=YOUR_KEY_HERE
```
(Replace `YOUR_KEY_HERE` with the real key from your Braintrust project settings.)

- [ ] **Step 2: Add the listener-aware constructor to RouterClient**

Current file is at `src/main/java/com/college_advisor/service/graph/client/RouterClient.java`.

Add these two imports after the existing imports:
```java
import dev.langchain4j.model.chat.listener.ChatModelListener;
import java.util.List;
```

Add this constructor after the existing `public RouterClient(String apiKey, String modelName)` constructor (leave the existing one completely untouched):
```java
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
```

- [ ] **Step 3: Verify it compiles**

```bash
./mvnw compile -q
```
Expected: BUILD SUCCESS with no errors.

- [ ] **Step 4: Commit**

```bash
git add src/main/resources/application-local.properties \
        src/main/java/com/college_advisor/service/graph/client/RouterClient.java
git commit -m "feat: add RouterClient listener overload and braintrust api-key config"
```

---

## Task 2: LlmCallEvent and LlmEventListener

**Files:**
- Create: `src/test/java/com/college_advisor/eval/listener/LlmCallEvent.java`
- Create: `src/test/java/com/college_advisor/eval/listener/LlmEventListener.java`
- Create: `src/test/java/com/college_advisor/eval/listener/LlmEventListenerTest.java`

- [ ] **Step 1: Write the failing test first**

Create `src/test/java/com/college_advisor/eval/listener/LlmEventListenerTest.java`:

```java
package com.college_advisor.eval.listener;

import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.listener.ChatModelErrorContext;
import dev.langchain4j.model.chat.listener.ChatModelRequestContext;
import dev.langchain4j.model.chat.listener.ChatModelResponseContext;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.response.ChatResponse;
import dev.langchain4j.model.output.TokenUsage;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class LlmEventListenerTest {

    /** Fires onRequest then onResponse with the SAME attributes map (as langchain4j does). */
    private void fireRequestResponse(LlmEventListener listener,
                                     int inputTokens, int outputTokens,
                                     String modelName) {
        ChatRequest req = ChatRequest.builder()
                .messages(List.of(UserMessage.from("hello")))
                .build();
        ChatResponse res = ChatResponse.builder()
                .aiMessage(AiMessage.from("hi"))
                .modelName(modelName)
                .tokenUsage(new TokenUsage(inputTokens, outputTokens))
                .build();

        Map<Object, Object> attrs = new HashMap<>();
        listener.onRequest(new ChatModelRequestContext(req, null, attrs));
        listener.onResponse(new ChatModelResponseContext(res, req, null, attrs));
    }

    @Test
    void capturesTokensAndLatency() {
        LlmEventListener listener = new LlmEventListener();
        fireRequestResponse(listener, 100, 50, "qwen-plus");

        List<LlmCallEvent> events = listener.snapshot();
        assertEquals(1, events.size());

        LlmCallEvent e = events.get(0);
        assertEquals("qwen-plus", e.modelName());
        assertEquals(100, e.promptTokens());
        assertEquals(50, e.completionTokens());
        assertEquals(150, e.totalTokens());
        assertTrue(e.latencyMs() >= 0, "latency should be non-negative");
    }

    @Test
    void resetClearsEvents() {
        LlmEventListener listener = new LlmEventListener();
        fireRequestResponse(listener, 10, 5, "qwen-plus");
        listener.reset();

        assertEquals(0, listener.snapshot().size());
        assertEquals(0, listener.totalTokens());
    }

    @Test
    void aggregatorsSum() {
        LlmEventListener listener = new LlmEventListener();
        fireRequestResponse(listener, 100, 50, "qwen-plus");
        fireRequestResponse(listener, 200, 80, "qwen-plus");

        assertEquals(300, listener.totalPromptTokens());
        assertEquals(130, listener.totalCompletionTokens());
        assertEquals(430, listener.totalTokens());
    }

    @Test
    void nullTokenUsageDefaultsToZero() {
        LlmEventListener listener = new LlmEventListener();

        ChatRequest req = ChatRequest.builder()
                .messages(List.of(UserMessage.from("test")))
                .build();
        ChatResponse res = ChatResponse.builder()
                .aiMessage(AiMessage.from("ok"))
                .modelName("qwen-plus")
                // no tokenUsage set → returns null
                .build();

        Map<Object, Object> attrs = new HashMap<>();
        listener.onRequest(new ChatModelRequestContext(req, null, attrs));
        listener.onResponse(new ChatModelResponseContext(res, req, null, attrs));

        LlmCallEvent e = listener.snapshot().get(0);
        assertEquals(0, e.promptTokens());
        assertEquals(0, e.completionTokens());
        assertEquals(0, e.totalTokens());
    }

    @Test
    void onErrorRecordsNegativeLatency() {
        LlmEventListener listener = new LlmEventListener();

        ChatRequest req = ChatRequest.builder()
                .messages(List.of(UserMessage.from("fail")))
                .build();
        Map<Object, Object> attrs = new HashMap<>();
        listener.onRequest(new ChatModelRequestContext(req, null, attrs));
        listener.onError(new ChatModelErrorContext(new RuntimeException("boom"), req, null, attrs));

        assertEquals(1, listener.snapshot().size());
        assertEquals("ERROR", listener.snapshot().get(0).modelName());
        assertTrue(listener.snapshot().get(0).latencyMs() >= 0);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./mvnw test -Dtest=LlmEventListenerTest -q 2>&1 | tail -10
```
Expected: compilation error — `LlmCallEvent` and `LlmEventListener` not found yet.

- [ ] **Step 3: Create LlmCallEvent**

Create `src/test/java/com/college_advisor/eval/listener/LlmCallEvent.java`:

```java
package com.college_advisor.eval.listener;

/**
 * Immutable snapshot of a single LLM call.
 * No dependency on Braintrust or graph code.
 */
public record LlmCallEvent(
        String modelName,
        int    promptTokens,
        int    completionTokens,
        int    totalTokens,
        long   latencyMs
) {}
```

- [ ] **Step 4: Create LlmEventListener**

Create `src/test/java/com/college_advisor/eval/listener/LlmEventListener.java`:

```java
package com.college_advisor.eval.listener;

import dev.langchain4j.model.chat.listener.ChatModelErrorContext;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.chat.listener.ChatModelRequestContext;
import dev.langchain4j.model.chat.listener.ChatModelResponseContext;
import dev.langchain4j.model.output.TokenUsage;

import java.util.Collections;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Captures per-call token usage and latency from langchain4j.
 * Thread-safe: safe for concurrent async nodes (planner route).
 * No dependency on Braintrust or graph code.
 */
public class LlmEventListener implements ChatModelListener {

    /** Shared key used to correlate onRequest → onResponse via the attributes map. */
    private static final Object NANOS_KEY = new Object();

    private final CopyOnWriteArrayList<LlmCallEvent> events = new CopyOnWriteArrayList<>();

    @Override
    public void onRequest(ChatModelRequestContext ctx) {
        ctx.attributes().put(NANOS_KEY, System.nanoTime());
    }

    @Override
    public void onResponse(ChatModelResponseContext ctx) {
        long latencyMs = computeLatency(ctx.attributes());

        TokenUsage usage = ctx.chatResponse().tokenUsage();
        int prompt     = usage != null && usage.inputTokenCount()  != null ? usage.inputTokenCount()  : 0;
        int completion = usage != null && usage.outputTokenCount() != null ? usage.outputTokenCount() : 0;
        int total      = usage != null && usage.totalTokenCount()  != null ? usage.totalTokenCount()  : prompt + completion;

        String modelName = ctx.chatResponse().modelName();
        if (modelName == null || modelName.isBlank()) {
            modelName = ctx.modelProvider() != null ? ctx.modelProvider().name() : "unknown";
        }

        events.add(new LlmCallEvent(modelName, prompt, completion, total, latencyMs));
    }

    @Override
    public void onError(ChatModelErrorContext ctx) {
        long latencyMs = computeLatency(ctx.attributes());
        events.add(new LlmCallEvent("ERROR", 0, 0, 0, latencyMs));
    }

    private long computeLatency(java.util.Map<Object, Object> attributes) {
        Long startNano = (Long) attributes.get(NANOS_KEY);
        return startNano != null ? (System.nanoTime() - startNano) / 1_000_000L : -1L;
    }

    /** Clears all captured events. Call before each eval case. */
    public void reset() {
        events.clear();
    }

    /** Returns an unmodifiable snapshot of all events since last reset(). */
    public List<LlmCallEvent> snapshot() {
        return Collections.unmodifiableList(new java.util.ArrayList<>(events));
    }

    public int totalPromptTokens() {
        return events.stream().mapToInt(LlmCallEvent::promptTokens).sum();
    }

    public int totalCompletionTokens() {
        return events.stream().mapToInt(LlmCallEvent::completionTokens).sum();
    }

    public int totalTokens() {
        return events.stream().mapToInt(LlmCallEvent::totalTokens).sum();
    }

    public long summedCallLatencyMs() {
        return events.stream().mapToLong(LlmCallEvent::latencyMs).filter(l -> l >= 0).sum();
    }
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
./mvnw test -Dtest=LlmEventListenerTest -q 2>&1 | tail -10
```
Expected: `Tests run: 5, Failures: 0, Errors: 0`

- [ ] **Step 6: Commit**

```bash
git add src/test/java/com/college_advisor/eval/listener/
git commit -m "feat: add LlmCallEvent and LlmEventListener for per-call token/latency capture"
```

---

## Task 3: BraintrustEvent and BraintrustLogger

**Files:**
- Create: `src/test/java/com/college_advisor/eval/braintrust/BraintrustEvent.java`
- Create: `src/test/java/com/college_advisor/eval/braintrust/BraintrustLogger.java`

- [ ] **Step 1: Create BraintrustEvent**

Create `src/test/java/com/college_advisor/eval/braintrust/BraintrustEvent.java`:

```java
package com.college_advisor.eval.braintrust;

import java.util.List;
import java.util.Map;

/**
 * One row in a Braintrust experiment.
 * No dependency on listener or graph code.
 */
public record BraintrustEvent(
        String              spanId,    // UUID for idempotent upsert
        String              input,     // raw user query
        String              output,    // state.response()
        Map<String, Object> metadata,  // route, nodeHistory, llmCalls breakdown
        Map<String, Object> metrics,   // totalLatencyMs, promptTokens, completionTokens, totalTokens, llmCallCount
        List<String>        tags       // [expectedRoute]
) {}
```

- [ ] **Step 2: Create BraintrustLogger**

Create `src/test/java/com/college_advisor/eval/braintrust/BraintrustLogger.java`:

```java
package com.college_advisor.eval.braintrust;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Thin REST client for the Braintrust experiment API.
 * No dependency on listener or graph code.
 */
public class BraintrustLogger {

    private static final String BASE_URL = "https://api.braintrustdata.com/v1";

    private final HttpClient   http;
    private final ObjectMapper mapper;
    private final String       apiKey;

    public BraintrustLogger(String apiKey) {
        this.apiKey  = apiKey;
        this.http    = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        this.mapper  = new ObjectMapper();
    }

    /**
     * Creates a new experiment in Braintrust.
     *
     * @param projectName    e.g. "college-advisor"
     * @param experimentName e.g. "college-advisor-2026-04-29T14-00-00"
     * @return the experiment ID to pass to logEvent()
     */
    public String createExperiment(String projectName, String experimentName) throws Exception {
        Map<String, Object> body = Map.of(
                "project_name", projectName,
                "name",         experimentName
        );
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(BASE_URL + "/experiment"))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type",  "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)))
                .timeout(Duration.ofSeconds(30))
                .build();

        HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new RuntimeException(
                    "Braintrust createExperiment failed: HTTP " + response.statusCode()
                    + " — " + response.body());
        }
        return mapper.readTree(response.body()).get("id").asText();
    }

    /**
     * Logs one eval row to an existing experiment.
     * HTTP errors are printed to stderr but do NOT throw — the eval loop continues.
     */
    public void logEvent(String experimentId, BraintrustEvent event) {
        try {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id",       event.spanId());
            row.put("input",    event.input());
            row.put("output",   event.output());
            row.put("metadata", event.metadata());
            row.put("metrics",  event.metrics());
            row.put("tags",     event.tags());

            Map<String, Object> body = Map.of("events", List.of(row));
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(BASE_URL + "/experiment/" + experimentId + "/insert"))
                    .header("Authorization", "Bearer " + apiKey)
                    .header("Content-Type",  "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)))
                    .timeout(Duration.ofSeconds(30))
                    .build();

            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                System.err.println("[BraintrustLogger] logEvent failed: HTTP "
                        + response.statusCode() + " — " + response.body());
            }
        } catch (Exception e) {
            System.err.println("[BraintrustLogger] logEvent error: " + e.getMessage());
        }
    }
}
```

- [ ] **Step 3: Verify it compiles**

```bash
./mvnw test-compile -q
```
Expected: BUILD SUCCESS.

- [ ] **Step 4: Commit**

```bash
git add src/test/java/com/college_advisor/eval/braintrust/
git commit -m "feat: add BraintrustEvent and BraintrustLogger REST client"
```

---

## Task 4: EvalCase and EvalDataset

**Files:**
- Create: `src/test/java/com/college_advisor/eval/dataset/EvalCase.java`
- Create: `src/test/java/com/college_advisor/eval/dataset/EvalDataset.java`

- [ ] **Step 1: Create EvalCase**

Create `src/test/java/com/college_advisor/eval/dataset/EvalCase.java`:

```java
package com.college_advisor.eval.dataset;

/**
 * One evaluation input. expectedRoute is used as a tag in Braintrust for filtering.
 */
public record EvalCase(String expectedRoute, String input) {}
```

- [ ] **Step 2: Create EvalDataset**

Cases are lifted directly from `RouterLlmTest` — 2-4 representative inputs per route.
Full route coverage in a small enough set to run quickly.

Create `src/test/java/com/college_advisor/eval/dataset/EvalDataset.java`:

```java
package com.college_advisor.eval.dataset;

import java.util.List;

/**
 * Fixed evaluation dataset. Inputs are taken from the existing full-pipeline LLM tests.
 * Add cases here as you add new test inputs to RouterLlmTest.
 */
public final class EvalDataset {

    private EvalDataset() {}

    public static final List<EvalCase> CASES = List.of(

        // ── clarify (3 cases) ────────────────────────────────────────────────
        new EvalCase("clarify", "Help me"),
        new EvalCase("clarify", "I am a junior in the STAT major. What should I take next?"),
        new EvalCase("clarify", "What is 2 + 2?"),

        // ── simple_task (3 cases) ────────────────────────────────────────────
        new EvalCase("simple_task", "What is STAT 432?"),
        new EvalCase("simple_task", "What are the prerequisites for STAT 425?"),
        new EvalCase("simple_task", "What do people say about STAT 432 on Reddit?"),

        // ── build_single_plan — recommender (2 cases) ────────────────────────
        new EvalCase("build_single_plan",
            "I am a sophomore in the STAT major and I have completed STAT 100 and STAT 200. "
            + "Recommend me 3 courses for next semester."),
        new EvalCase("build_single_plan",
            "I want to go to grad school in statistics. I am a junior in the STAT major "
            + "and have completed STAT 200, STAT 400, and STAT 410. What courses should I prioritize?"),

        // ── build_single_plan — scheduler (1 case) ───────────────────────────
        new EvalCase("build_single_plan",
            "I am a junior in the STAT major and I want to take STAT 400 and STAT 432 "
            + "next semester. Help me build a schedule that avoids Friday classes."),

        // ── planner (2 cases) ────────────────────────────────────────────────
        new EvalCase("planner",
            "I am a sophomore in the STAT major and have completed STAT 100 and STAT 107. "
            + "Recommend me courses for next semester, then build me a schedule around them."),
        new EvalCase("planner",
            "I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. "
            + "First recommend the 2-3 courses I should take next semester to fill my prerequisite gaps, "
            + "then separately map out a semester-by-semester degree plan for my remaining 2 years.")
    );
}
```

- [ ] **Step 3: Verify it compiles**

```bash
./mvnw test-compile -q
```
Expected: BUILD SUCCESS.

- [ ] **Step 4: Commit**

```bash
git add src/test/java/com/college_advisor/eval/dataset/
git commit -m "feat: add EvalCase and EvalDataset with representative inputs from existing LLM tests"
```

---

## Task 5: BraintrustEvalTest (main orchestrator)

**Files:**
- Create: `src/test/java/com/college_advisor/eval/BraintrustEvalTest.java`

- [ ] **Step 1: Create BraintrustEvalTest**

Create `src/test/java/com/college_advisor/eval/BraintrustEvalTest.java`:

```java
package com.college_advisor.eval;

import com.college_advisor.eval.braintrust.BraintrustEvent;
import com.college_advisor.eval.braintrust.BraintrustLogger;
import com.college_advisor.eval.dataset.EvalCase;
import com.college_advisor.eval.dataset.EvalDataset;
import com.college_advisor.eval.listener.LlmCallEvent;
import com.college_advisor.eval.listener.LlmEventListener;
import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.tools.*;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.InputStream;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Braintrust evaluation harness.
 *
 * Runs all EvalDataset.CASES through the full graph pipeline,
 * captures token usage and latency via LlmEventListener,
 * and logs results to a new Braintrust experiment.
 *
 * Run: ./mvnw test -Dtest=BraintrustEvalTest
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class BraintrustEvalTest {

    private static final String PROJECT_NAME = "college-advisor";
    private static final DateTimeFormatter FMT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH-mm-ss").withZone(ZoneOffset.UTC);

    private static HikariDataSource    dataSource;
    private static CompiledGraph<MainState> graph;
    private static LlmEventListener    listener;
    private static BraintrustLogger    braintrust;
    private static String              experimentId;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = BraintrustEvalTest.class.getClassLoader()
                .getResourceAsStream("application-local.properties")) {
            props.load(in);
        }

        String dashApiKey      = props.getProperty("dashscope.api-key");
        String modelName       = props.getProperty("dashscope.model-name");
        String embeddingModel  = props.getProperty("dashscope.embedding-model-name");
        String tavilyApiKey    = props.getProperty("tavily.api-key");
        String braintrustKey   = props.getProperty("braintrust.api-key");

        // 1. Shared listener — injected into both ChatModel and RouterClient
        listener = new LlmEventListener();
        List<ChatModelListener> listenerList = List.of(listener);

        // 2. ChatModel with listener
        OpenAiChatModel chatModel = OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(dashApiKey)
                .modelName(modelName)
                .temperature(0.2)
                .listeners(listenerList)
                .build();

        // 3. RouterClient with listener (uses the new overload)
        RouterClient routerClient = new RouterClient(dashApiKey, modelName, listenerList);

        // 4. DB + tools (same pattern as SimpleTaskLlmTest)
        HikariConfig hikari = new HikariConfig();
        hikari.setJdbcUrl(props.getProperty("spring.datasource.url"));
        hikari.setUsername(props.getProperty("spring.datasource.username").strip());
        hikari.setPassword(props.getProperty("spring.datasource.password").strip());
        dataSource = new HikariDataSource(hikari);

        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        EmbeddingClient embeddingClient = new EmbeddingClient(dashApiKey, embeddingModel, 768);
        TavilyClient tavily = new TavilyClient(tavilyApiKey);

        CourseDataTools  courseData  = new CourseDataTools(jdbc, embeddingClient);
        CourseSectionTools sections  = new CourseSectionTools(jdbc);
        GraduationTools   graduation = new GraduationTools(jdbc);
        ProfessorRatingTools profRating = new ProfessorRatingTools(tavily);
        SkillTools        skill      = new SkillTools(jdbc);

        // 5. Compile full production graph
        graph = ParentGraph.build(routerClient, chatModel,
                courseData, sections, graduation, profRating, skill);

        // 6. Create Braintrust experiment
        braintrust = new BraintrustLogger(braintrustKey);
        String experimentName = PROJECT_NAME + "-" + FMT.format(Instant.now());
        experimentId = braintrust.createExperiment(PROJECT_NAME, experimentName);
        System.out.println("[BraintrustEvalTest] experiment: " + experimentName + " id=" + experimentId);
    }

    @AfterAll
    static void tearDown() {
        if (dataSource != null) dataSource.close();
    }

    @Test
    @Order(1)
    void runEval() throws Exception {
        for (EvalCase evalCase : EvalDataset.CASES) {
            runSingleCase(evalCase);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────

    private void runSingleCase(EvalCase evalCase) throws Exception {
        listener.reset();

        long wallStart = System.currentTimeMillis();
        MainState state;
        try {
            state = graph.invoke(Map.of("userInput", evalCase.input())).get();
        } catch (Exception e) {
            System.err.printf("[BraintrustEvalTest] graph.invoke failed for [%s]: %s%n",
                    evalCase.input(), e.getMessage());
            return;
        }
        long wallLatencyMs = System.currentTimeMillis() - wallStart;

        List<LlmCallEvent> calls = listener.snapshot();

        // Build per-call detail for metadata
        List<Map<String, Object>> llmCallMaps = new ArrayList<>();
        for (LlmCallEvent call : calls) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("model",            call.modelName());
            m.put("promptTokens",     call.promptTokens());
            m.put("completionTokens", call.completionTokens());
            m.put("totalTokens",      call.totalTokens());
            m.put("latencyMs",        call.latencyMs());
            llmCallMaps.add(m);
        }

        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("route",         state.routeDecision());
        metadata.put("nodeHistory",   state.nodeHistory());
        metadata.put("expectedRoute", evalCase.expectedRoute());
        metadata.put("llmCalls",      llmCallMaps);

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("totalLatencyMs",    wallLatencyMs);
        metrics.put("promptTokens",      listener.totalPromptTokens());
        metrics.put("completionTokens",  listener.totalCompletionTokens());
        metrics.put("totalTokens",       listener.totalTokens());
        metrics.put("llmCallCount",      calls.size());

        BraintrustEvent event = new BraintrustEvent(
                UUID.randomUUID().toString(),
                evalCase.input(),
                state.response() != null ? state.response() : "",
                metadata,
                metrics,
                List.of(evalCase.expectedRoute())
        );

        braintrust.logEvent(experimentId, event);

        System.out.printf("[eval] route=%-20s | latency=%5dms | tokens=%4d (p=%4d c=%3d) | calls=%d%n",
                state.routeDecision(), wallLatencyMs,
                listener.totalTokens(), listener.totalPromptTokens(),
                listener.totalCompletionTokens(), calls.size());
    }
}
```

- [ ] **Step 2: Run the eval test**

```bash
./mvnw test -Dtest=BraintrustEvalTest 2>&1 | grep -E "\[eval\]|\[BraintrustEvalTest\]|FAILED|ERROR|BUILD"
```

Expected console output (one line per case, values will vary):
```
[BraintrustEvalTest] experiment: college-advisor-2026-04-29T... id=<uuid>
[eval] route=clarify              | latency=  820ms | tokens= 312 (p= 280 c= 32) | calls=2
[eval] route=clarify              | latency=  750ms | tokens= 298 (p= 265 c= 33) | calls=2
...
BUILD SUCCESS
```

- [ ] **Step 3: Verify results in Braintrust UI**

Open your Braintrust project in the browser. Confirm:
1. A new experiment named `college-advisor-<timestamp>` appears
2. It contains 11 rows (one per EvalCase)
3. Each row has `metrics.totalLatencyMs`, `metrics.promptTokens`, `metrics.completionTokens`, `metrics.totalTokens`
4. Rows are tagged with route names (`clarify`, `simple_task`, etc.)
5. `metadata.llmCalls` shows per-call breakdown

- [ ] **Step 4: Commit**

```bash
git add src/test/java/com/college_advisor/eval/BraintrustEvalTest.java
git commit -m "feat: add BraintrustEvalTest — full eval harness wiring listener, graph, and Braintrust logger"
```

---

## Verification Summary

**Fast check (unit tests only, no LLM calls):**
```bash
./mvnw test -Dtest=LlmEventListenerTest
```
Expected: 5 tests, all pass.

**Full eval run (hits DashScope API + Supabase + Braintrust, ~5-15 min):**
```bash
./mvnw test -Dtest=BraintrustEvalTest
```
Expected: 11 cases logged, experiment visible in Braintrust UI.

**Prompt comparison workflow:**
1. Edit a `SYSTEM_PROMPT` constant in any node file (e.g. `SimpleTaskNode.java`)
2. Re-run `./mvnw test -Dtest=BraintrustEvalTest`
3. In Braintrust UI: select both experiments → "Compare" → filter by route tag
4. Diff `metrics.promptTokens` and `metrics.totalLatencyMs` side by side

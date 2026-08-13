# Braintrust Evaluation Harness — Design Spec

**Date:** 2026-04-29  
**Scope:** Token consumption + latency observability via Braintrust. No accuracy scoring yet.  
**Motivation:** Enable prompt A/B comparison and dev-time tuning by capturing per-LLM-call token usage and end-to-end latency for each graph invocation.

---

## Goals

- See token consumption (prompt / completion / total) and latency per graph invocation
- Compare two prompt versions side by side in Braintrust UI
- Dataset = reuse existing full-pipeline LLM test cases
- Decoupled enough to add accuracy scoring, new metrics, or swap eval platform later

## Non-Goals (for now)

- Accuracy / quality scoring
- CI/CD integration
- Real-time streaming metrics

---

## Package Layout

```
src/test/java/com/college_advisor/eval/
    listener/
        LlmCallEvent.java          ← pure data record, no Braintrust knowledge
        LlmEventListener.java      ← implements ChatModelListener, no Braintrust knowledge
    braintrust/
        BraintrustEvent.java       ← data record for one logged row
        BraintrustLogger.java      ← REST client only, no graph/listener knowledge
    dataset/
        EvalCase.java              ← record: expectedRoute + input
        EvalDataset.java           ← static list, inputs taken from existing LLM tests
    BraintrustEvalTest.java        ← orchestrator: wires listener → graph → logger
```

**Decoupling contract:**
- `listener/` has zero imports from `braintrust/` or graph code
- `braintrust/` has zero imports from `listener/` or graph code
- `BraintrustEvalTest` is the only class that knows about all three layers

---

## Components

### `LlmCallEvent` (record)

```
modelName, promptTokens, completionTokens, totalTokens, latencyMs
```

Null-safe: if DashScope returns no `TokenUsage`, all token fields default to 0.

### `LlmEventListener` (implements `ChatModelListener`)

- `onRequest`: stores `System.nanoTime()` into the request's `attributes` map (langchain4j passes the same map instance to `onResponse`)
- `onResponse`: calculates latency, reads `TokenUsage`, appends `LlmCallEvent` to a `CopyOnWriteArrayList` (safe for concurrent async nodes in `planner` route)
- `onError`: appends a zero-token event with negative latency (preserves call count)
- `reset()`: clears list between eval cases
- `snapshot()`: returns unmodifiable copy
- Convenience aggregators: `totalPromptTokens()`, `totalCompletionTokens()`, `totalTokens()`, `summedCallLatencyMs()`

### `BraintrustLogger`

Uses `java.net.http.HttpClient` + Jackson (already in pom.xml).

```
createExperiment(projectName, experimentName) → experimentId
logEvent(experimentId, BraintrustEvent)       → POST /v1/experiment/{id}/insert
```

HTTP errors on `logEvent` are logged to stderr but do NOT fail the eval loop.

### `BraintrustEvent` (record)

```
spanId       UUID string for dedup
input        user query string
output       state.response()
metadata     Map: route, nodeHistory, expectedRoute, llmCalls (List of per-call detail)
metrics      Map: totalLatencyMs, promptTokens, completionTokens, totalTokens, llmCallCount
tags         List<String>: [expectedRoute]
```

### `EvalCase` / `EvalDataset`

`EvalCase` is a record: `expectedRoute` + `input`.

Dataset entries are lifted directly from existing test files:
- `SimpleTaskLlmTest` → `simple_task` cases
- `ClarifyLlmTest` / `ClarifyNodeLlmTest` → `clarify` cases
- `BuildSinglePlanLlmTest` → `build_single_plan` cases
- `MultiTaskPlanLlmTest` → `planner` cases

### `BraintrustEvalTest`

`@BeforeAll`:
1. Load `application-local.properties` (same pattern as existing tests)
2. Instantiate `LlmEventListener`
3. Build `OpenAiChatModel` with `.listeners(List.of(listener))`
4. Build `RouterClient` with new overload: `RouterClient(apiKey, modelName, listeners)` — shares same listener
5. Build graph: `ParentGraph.build(routerClient, chatModel, tools...)` or no-DB overload
6. `braintrust.createExperiment("college-advisor", "college-advisor-{timestamp}")`

Per case (`runSingleCase`):
1. `listener.reset()`
2. Record wall-clock start
3. `graph.invoke(Map.of("userInput", input)).get()`
4. Calculate wall latency
5. `listener.snapshot()` → build `BraintrustEvent`
6. `braintrust.logEvent(experimentId, event)`
7. Print console summary line

---

## RouterClient Change

Add one constructor overload (existing constructor untouched):

```java
public RouterClient(String apiKey, String modelName, List<ChatModelListener> listeners)
```

This is the only production-code change. `LlmConfig` continues using the existing no-listener constructor.

---

## Configuration

Add to `application-local.properties`:
```
braintrust.api-key=<your-key>
```

---

## Prompt Comparison Workflow

1. Edit `SYSTEM_PROMPT` in any node (e.g. `SimpleTaskNode`, `RouterClient.buildPrompt()`)
2. Run `./mvnw test -Dtest=BraintrustEvalTest`
3. New experiment appears in Braintrust UI with a timestamp name
4. Compare two experiments side by side: filter by tag (route), compare `promptTokens` and `totalLatencyMs`

---

## Extension Points (future)

| What to add | Where |
|---|---|
| Accuracy / quality score | `BraintrustEvent` gains a `scores` map; `BraintrustEvalTest.runSingleCase` computes score before `logEvent` |
| New metric (e.g. tool call count) | Add field to `BraintrustEvent.metrics`; `LlmEventListener` already tracks `llmCallCount` |
| Swap eval platform (LangSmith) | Replace `BraintrustLogger` with `LangSmithLogger`, same interface |
| Dynamic dataset from logs | Replace `EvalDataset.CASES` with a loader; `EvalCase` record stays unchanged |
| Per-node span hierarchy | `BraintrustEvent` gains `parentId`; `LlmCallEvent` gains node name (available from `attributes`) |

---

## Verification

Run: `./mvnw test -Dtest=BraintrustEvalTest`

Expected:
- Console prints one summary line per case: `route=X | latency=Yms | tokens=Z (p=A c=B) | calls=N`
- Braintrust UI shows new experiment with all cases logged
- Each case has `metrics.promptTokens`, `metrics.completionTokens`, `metrics.totalLatencyMs` populated

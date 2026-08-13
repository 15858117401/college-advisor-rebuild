# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Run the application (starts on port 8080)
./mvnw spring-boot:run

# Build skipping tests
./mvnw clean package -DskipTests

# Run all tests
./mvnw test

# Graph skeleton tests (no Spring, no network — fast)
./mvnw test -Dtest=GraphSkeletonTest

# Live LLM routing tests (hits Gemini API, ~15s)
./mvnw test -Dtest=RouterLlmTest

# SimpleTask integration test (hits Gemini API + Supabase DB, slow)
./mvnw test -Dtest=SimpleTaskMockedRouterTest

# SimpleTask LLM test (hits Gemini API + Supabase DB)
./mvnw test -Dtest=SimpleTaskLlmTest

# Spring context test (requires local profile)
./mvnw test -Dtest=CollegeAdvisorApplicationTests

# RAG parser unit tests (no Spring, no network — fast)
./mvnw test -Dtest=StatMdParserTest

# Plan generation LLM test (hits Gemini API, no DB)
./mvnw test -Dtest=BuildSinglePlanLlmTest

# Multi-task plan LLM test (hits Gemini API, no DB)
./mvnw test -Dtest=MultiTaskPlanLlmTest

# Clarify node LLM tests (hits Gemini API)
./mvnw test -Dtest=ClarifyLlmTest
./mvnw test -Dtest=ClarifyNodeLlmTest

# Full sub-agent pipeline test (hits Gemini API + Supabase DB, slow)
./mvnw test -Dtest=RecommenderSingleTaskLlmTest

# Scheduler full pipeline test (hits Gemini API + Supabase DB, slow)
./mvnw test -Dtest=SchedulerLlmTest

# CoursePlanner full pipeline test (hits Gemini API + Supabase DB, slow)
./mvnw test -Dtest=CoursePlannerLlmTest
```

## Architecture

**No REST API.** The system is graph-only — no controllers or HTTP endpoints. Entry points are `Main.main()` (skeleton runner) and `CollegeAdvisorApplication.main()` (Spring Boot, auto-activates `local` profile). Requests are submitted programmatically to the compiled `StateGraph`.

Spring Boot 4.0.5 (Java 17) multi-agent college advising system using **langgraph4j 1.8.13** for graph orchestration and **langchain4j 1.13.1** for all LLM interactions. `qwen-plus` (via DashScope / Alibaba Cloud) is the model, configured in `src/main/resources/application-local.properties`. Both `ChatModel` and `EmbeddingClient` use `OpenAiChatModel`/`OpenAiEmbeddingModel` pointed at DashScope's OpenAI-compatible endpoint (`https://dashscope.aliyuncs.com/compatible-mode/v1`).

### Graph (`service/graph/`)

`ParentGraph.java` compiles a `StateGraph<MainState>` with the following public `build()` overloads:

| Overload | Usage |
|----------|-------|
| `build()` | Defaults to `build("simple_task")` |
| `build(RouterClient, ChatModel, CourseDataTools, CourseSectionTools, GraduationTools, ProfessorRatingTools, SkillTools)` | Production — all nodes real |
| `build(RouterClient, ChatModel)` | No-DB tests — real router + planning nodes, stub ExecutionSubgraph |
| `build(String forceRoute, ChatModel, CourseDataTools, CourseSectionTools, GraduationTools, ProfessorRatingTools)` | Stub-router tests — real SimpleTaskNode |
| `build(String forceRoute, ChatModel)` | Stub-router tests — real planning nodes, no DB |
| `build(String forceRoute)` | Skeleton tests — all stub nodes |

Every request enters `router`, which calls the LLM to classify intent, then branches:

| Route | Node(s) | When |
|-------|---------|------|
| `clarify` | ClarifyNode → output | Ambiguous input |
| `simple_task` | SimpleTaskNode → output | Simple lookup/calculation |
| `build_single_plan` | SingleTaskNode → execution_subgraph | Single sub-agent task |
| `planner` | MultiTaskNode → execution_subgraph | Multi-task composite |

Error path: any node sets `currentError` in state → `ErrorHandlerNode` → retry or `FatalErrorNode` → END.

### ReactAgent pattern (`service/agent/ReactAgent.java`)

All tool-using nodes go through `ReactAgent` — the single error-management layer. Nodes never build `AiServices` directly.

```java
// In node constructor
this.reactAgent = new ReactAgent(model, SYSTEM_PROMPT, courseData, sections, graduation, profRating);

// In apply()
ReactResult result = reactAgent.run(state.userInput());
if (!result.success()) {
    ErrorInfo err = new ErrorInfo("node_name", "AGENT_ERROR", result.error(), true);
    return Map.of("errorContext", new ErrorContext(err, state.errorContext().nodeRetries(), null),
                  "nodeHistory", "node_name");
}
return Map.of("response", result.content(), "nodeHistory", "node_name");
```

`ReactAgent` internals:
- Wraps langchain4j `AiServices` + `CollegeAdvisorAgent` interface (`String chat(@UserMessage String)`)
- Auto-injects `TerminateTool` so the LLM has an explicit exit point (prevents spinning to tool call limit)
- `run()` returns `ReactResult` — never throws. `ReactResult` is a record: `success`, `content`, `error`
- Retry with exponential backoff (1s/2s/4s) for transient errors: 429, 503, timeout, rate limit (max 3 retries)
- Fatal errors (401, context overflow, max tool calls) fail immediately with a classified label
- `BASE_SYSTEM_PROMPT` instructs LLM to call `terminate()` when done or when no tool can help
- Each node passes its own `SYSTEM_PROMPT` as `additionalPrompt` — appended after `BASE_SYSTEM_PROMPT`
- `DEFAULT_MAX_TOOL_CALLS = 10`

Nodes using this pattern: `SimpleTaskNode`, `RecommenderNode`, `SchedulerNode`.

**Exception — `CoursePlannerNode`**: uses `AiServices` directly (no `ReactAgent`, no `TerminateTool`) because the LLM was routing its final answer through `terminate()` arguments, causing `agent.chat()` to return an empty string. The SYSTEM_PROMPT instructs "Call exactly TWO tools" to prevent runaway tool call loops. Error handling mirrors the same pattern (catch → set `errorContext`).

### ExecutionSubgraph (`service/graph/nodes/executionNodes/ExecutionSubgraph`)

A separate compiled subgraph for multi-step planning routes:

```
START → dispatcher → {recommender | scheduler | course_planner}
                           ↓ (all done)              ↓ (more tasks)
                      subgraph_output ←──── dispatcher (loop)
                           ↓
                          END
```

`DispatcherNode` picks the next ready task and writes `currentTaskId`. Each sub-agent node processes the task `goal`, appends a `TaskResult`, then routes back to `dispatcher` or `subgraph_output`. All three sub-agent nodes (`RecommenderNode`, `SchedulerNode`, `CoursePlannerNode`) are fully implemented.

**STAT 400 section types**: Only course in the DB with separate `Lecture` and `Discussion` section_types — the scheduler must include CRNs for both. `SchedulerNode.SYSTEM_PROMPT` documents this explicitly.

### Tools (`service/tools/`)

Six domain classes with `@Tool` annotations — langchain4j generates schemas automatically:

| Class | Tools | Dependencies |
|-------|-------|-------------|
| `CourseDataTools` | `searchCourses`, `getCourseDetails`, `filterCourses`, `findAvailableCourses`, `findCoursesByPrerequisite`, `findCoursesByInstructor`, `getPrerequisiteChain` | `JdbcTemplate` + `EmbeddingClient` |
| `CourseSectionTools` | `getCourseSections` | `JdbcTemplate` |
| `GraduationTools` | `getGraduationRequirements` | `JdbcTemplate` |
| `ProfessorRatingTools` | `searchRateMyProfessor`, `searchReddit` | `TavilyClient` |
| `SkillTools` | `loadSkill` | `JdbcTemplate` |
| `TerminateTool` | `terminate` | none — auto-injected by `ReactAgent` |

`SkillTools` is recommender-exclusive. `TerminateTool` is injected automatically by `ReactAgent` — never pass it manually. `TavilyClient` wraps the Tavily search API with hand-rolled HTTP (no langchain4j equivalent at version 1.13.1). `EmbeddingClient` wraps `GoogleAiEmbeddingModel` from langchain4j.

`SkillTools.loadSkill()` constraint: `@Tool` description and `RecommenderNode.SYSTEM_PROMPT` both instruct the LLM to call it at most once, as the very first tool call, using a CoT reasoning step to decide which skill applies.

### Skills (`src/main/resources/skills/`)

Static strategy documents loaded at runtime by `SkillTools.loadSkill()`. Two skills exist: `minimal_graduation` and `grad_school_prep`. Add new skills by dropping a `.md` file and adding a `prefetch` case in `SkillTools`.

### State (`service/graph/state/`)

**`MainState`** extends langgraph4j `AgentState`. Registered channels:

| Field | Channel | Type |
|-------|---------|------|
| `errorContext` | `base` | `ErrorContext` |
| `nodeHistory` | `appender` | `List<String>` |
| `taskContext` | `base` | `TaskContext` |
| `userPreferences` | `base` | `UserPreferences` |

Dynamic fields (no channel registration): `userInput`, `routeDecision`, `response`, `currentTaskId`.

`TaskContext` is immutable and `Serializable`: wraps `plan` + `result`. Update via `state.taskContext().withPlan(...)` or `.withResult(...)`.

`UserPreferences` is a `Serializable` record of seven optional scheduling/course preferences, each wrapped in `PreferenceField<T>` which tracks `value` + `autoFilled`. `autoFilled=true` means the planner inferred a default (may be silently relaxed); `autoFilled=false` means the student stated it explicitly (notify before relaxing). Fields: `noEarlierThan`, `noLaterThan`, `avoidDays`, `noMandatoryAttendance`, `workload`, `difficulty`, `minGpa`. Use `UserPreferences.empty()` as the default.

**`SubgraphState`** extends `AgentState` — used exclusively within `ExecutionSubgraph`. Registered channels: `errorContext` (base), `taskResults` (appender), `nodeHistory` (appender), `plan` (base), `userPreferences` (base). Dynamic fields: `userInput`, `currentTaskId`.

`Plan` is `record Plan(List<List<PlanTask>> chains)`. Outer list = parallel chains; within each chain tasks run sequentially. `PlanTask` fields: `id`, `taskType` (`recommender` | `scheduler` | `course_planner`), `goal`, `constraints`. Both implement `Serializable`.

**Important:** Any custom object stored in state must implement `java.io.Serializable`.

### Node contract

Each node implements `NodeAction<S>` (S = `MainState` or `SubgraphState`):
- `apply()` — does work, returns `Map<String, Object>` of state updates; always include `"nodeHistory"` with the node name
- On agent failure: set `"errorContext"` with a new `ErrorContext(ErrorInfo(...), state.errorContext().nodeRetries(), null)`
- `route()` — reads state, returns next node name; always check `state.currentError() != null` first

Nodes have two constructors: no-arg for skeleton/test (null reactAgent), full-arg for production.

### Router (`service/graph/client/RouterClient.java`)

Wraps `OpenAiChatModel` via DashScope (`temperature=0`, `maxTokens=800`). `classify(String userInput)` calls `buildPrompt()` (70-line routing rules) → `model.chat()` → `parseRoute()` (extracts last `category:` token, maps `composite_task` → `planner`). Falls back to `simple_task` on any error.

### Spring wiring

`LlmConfig` (`@Configuration`) produces: `RouterClient`, `EmbeddingClient`, `TavilyClient`, `OpenAiChatModel` (temp=0.2, DashScope), `CourseDataTools`, `CourseSectionTools`, `GraduationTools`, `ProfessorRatingTools`, `SkillTools`, `CompiledGraph<MainState>`. `CollegeAdvisorApplicationTests` requires `@ActiveProfiles("local")`.

Properties in `application-local.properties`:
- `dashscope.api-key`
- `dashscope.model-name`
- `dashscope.embedding-model-name`
- `tavily.api-key`
- `spring.datasource.url/username/password`

**Gotcha:** Non-Spring tests call `.strip()` on the password value; Spring Boot does not. Trailing whitespace on `spring.datasource.password` causes `CollegeAdvisorApplicationTests` to fail with `PSQLException: password authentication failed`.

### Testing pattern

- `GraphSkeletonTest` — no Spring, no network; `build(forceRoute)` with stub nodes. Run first for any new node.
- `SimpleTaskMockedRouterTest` — no Spring; stub router + real `ChatModel` + real DB.
- `SimpleTaskLlmTest` / `RecommenderSingleTaskLlmTest` / `SchedulerLlmTest` / `CoursePlannerLlmTest` — no Spring; full production pipeline with real router + real DB.
- `BuildSinglePlanLlmTest` / `MultiTaskPlanLlmTest` — no Spring, no DB; tests plan generation only.
- `CollegeAdvisorApplicationTests` — full Spring context, requires `@ActiveProfiles("local")` and running DB.

### RAG ingestion pipeline (`service/rag/`)

Offline pipeline: `stat.md` → `StatMdParser` → `EmbeddingClient` → Supabase/pgvector. Two standalone entry points (no Spring):
- `IngestApplication` — upserts `graduation_requirements`, `courses`, `course_sections`
- `RagIngestApplication` — writes `course_chunks` with richer metadata

Run with `./mvnw exec:java -Dexec.mainClass=com.college_advisor.ingest.RagIngestApplication`.

**Note:** `service/rag/` is write-only — retrieval (vector search) is in `CourseDataTools.searchCourses()`.

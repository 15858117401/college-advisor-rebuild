# Multi-Turn Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent multi-turn conversation support so the graph can reference previous turns when routing and generating responses.

**Architecture:** `ConversationService` wraps `graph.invoke()`, loads history from Supabase before each call and writes results after. History is injected via three new `MainState` fields. Router, ClarifyNode, and planning nodes read from `state.conversationHistory()` — ReactAgent is unchanged.

**Tech Stack:** Spring Boot + JdbcTemplate, Supabase (PostgreSQL), langgraph4j `MainState` channels, existing DashScope `ChatModel`.

---

## File Map

| Action | File |
|--------|------|
| Create | `src/main/java/com/college_advisor/service/conversation/ConversationMessage.java` |
| Create | `src/main/java/com/college_advisor/service/conversation/ConversationStore.java` |
| Create | `src/main/java/com/college_advisor/service/conversation/SupabaseConversationStore.java` |
| Create | `src/main/java/com/college_advisor/service/conversation/ConversationService.java` |
| Modify | `src/main/java/com/college_advisor/service/graph/state/MainState.java` |
| Modify | `src/main/java/com/college_advisor/service/graph/client/RouterClient.java` |
| Modify | `src/main/java/com/college_advisor/service/graph/nodes/routerNode/RouterNode.java` |
| Modify | `src/main/java/com/college_advisor/service/graph/nodes/executionNodes/ClarifyNode/ClarifyNode.java` |
| Modify | `src/main/java/com/college_advisor/service/graph/nodes/executionNodes/PlanNode/SingleTaskNode/SingleTaskNode.java` |
| Modify | `src/main/java/com/college_advisor/service/graph/nodes/executionNodes/PlanNode/MultiTaskNode/MultiTaskNode.java` |
| Modify | `src/main/java/com/college_advisor/config/LlmConfig.java` |
| Create | `src/test/java/com/college_advisor/service/conversation/ConversationStoreTest.java` |
| Create | `src/test/java/com/college_advisor/service/conversation/MultiTurnLlmTest.java` |

---

## Task 1: Run DB migration in Supabase

**Files:**
- (no Java file — run SQL in Supabase dashboard SQL editor)

- [ ] **Step 1: Open Supabase SQL editor and run the following SQL**

```sql
CREATE TABLE IF NOT EXISTS users (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid REFERENCES users(id),
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid REFERENCES conversations(id),
    role            text NOT NULL CHECK (role IN ('user', 'assistant')),
    content         text NOT NULL,
    turn_index      int  NOT NULL,
    created_at      timestamptz DEFAULT now()
);
```

- [ ] **Step 2: Verify the tables exist**

Run in Supabase SQL editor:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('users', 'conversations', 'messages');
```

Expected: 3 rows returned.

- [ ] **Step 3: Commit a note**

```bash
git commit --allow-empty -m "chore: db migration — add users/conversations/messages tables (run manually in Supabase)"
```

---

## Task 2: ConversationMessage record + MainState fields

**Files:**
- Create: `src/main/java/com/college_advisor/service/conversation/ConversationMessage.java`
- Modify: `src/main/java/com/college_advisor/service/graph/state/MainState.java`

- [ ] **Step 1: Create ConversationMessage**

Create file `src/main/java/com/college_advisor/service/conversation/ConversationMessage.java`:

```java
package com.college_advisor.service.conversation;

import java.io.Serializable;

public record ConversationMessage(String role, String content, int turnIndex)
        implements Serializable {}
```

- [ ] **Step 2: Add three fields to MainState.SCHEMA**

In `MainState.java`, add to the `static {}` block after `SCHEMA.put("userPreferences", ...)`:

```java
SCHEMA.put("conversationId",      Channels.base(() -> ""));
SCHEMA.put("userId",              Channels.base(() -> ""));
SCHEMA.put("conversationHistory", Channels.base(ArrayList::new));
```

- [ ] **Step 3: Add three accessor methods to MainState**

Add after `userPreferences()`:

```java
public String conversationId() {
    return this.<String>value("conversationId").orElse("");
}

public String userId() {
    return this.<String>value("userId").orElse("");
}

@SuppressWarnings("unchecked")
public List<ConversationMessage> conversationHistory() {
    return this.<List<ConversationMessage>>value("conversationHistory").orElseGet(ArrayList::new);
}
```

Also add the import at the top of `MainState.java`:

```java
import com.college_advisor.service.conversation.ConversationMessage;
```

- [ ] **Step 4: Build to verify compilation**

```bash
./mvnw clean package -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/college_advisor/service/conversation/ConversationMessage.java \
        src/main/java/com/college_advisor/service/graph/state/MainState.java
git commit -m "feat: add ConversationMessage record and MainState conversation fields"
```

---

## Task 3: ConversationStore interface + SupabaseConversationStore

**Files:**
- Create: `src/main/java/com/college_advisor/service/conversation/ConversationStore.java`
- Create: `src/main/java/com/college_advisor/service/conversation/SupabaseConversationStore.java`

- [ ] **Step 1: Create ConversationStore interface**

```java
package com.college_advisor.service.conversation;

import java.util.List;

public interface ConversationStore {
    /** Creates a new conversation for the given user, returns the new conversation UUID. */
    String createConversation(String userId);

    /** Appends a message to an existing conversation. */
    void appendMessage(String conversationId, String role, String content);

    /** Returns all messages for a conversation, ordered by turn_index ascending. */
    List<ConversationMessage> loadHistory(String conversationId);
}
```

- [ ] **Step 2: Create SupabaseConversationStore**

```java
package com.college_advisor.service.conversation;

import org.springframework.jdbc.core.JdbcTemplate;

import java.util.List;

public class SupabaseConversationStore implements ConversationStore {

    private final JdbcTemplate jdbc;

    public SupabaseConversationStore(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public String createConversation(String userId) {
        return jdbc.queryForObject(
                "INSERT INTO conversations (user_id) VALUES (?::uuid) RETURNING id::text",
                String.class, userId);
    }

    @Override
    public void appendMessage(String conversationId, String role, String content) {
        int nextIndex = jdbc.queryForObject(
                "SELECT COALESCE(MAX(turn_index), -1) + 1 FROM messages WHERE conversation_id = ?::uuid",
                Integer.class, conversationId);
        jdbc.update(
                "INSERT INTO messages (conversation_id, role, content, turn_index) VALUES (?::uuid, ?, ?, ?)",
                conversationId, role, content, nextIndex);
    }

    @Override
    public List<ConversationMessage> loadHistory(String conversationId) {
        return jdbc.query(
                "SELECT role, content, turn_index FROM messages WHERE conversation_id = ?::uuid ORDER BY turn_index",
                (rs, rowNum) -> new ConversationMessage(
                        rs.getString("role"),
                        rs.getString("content"),
                        rs.getInt("turn_index")),
                conversationId);
    }
}
```

- [ ] **Step 3: Build to verify**

```bash
./mvnw clean package -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add src/main/java/com/college_advisor/service/conversation/
git commit -m "feat: add ConversationStore interface and SupabaseConversationStore"
```

---

## Task 4: ConversationStoreTest (requires Supabase DB)

**Files:**
- Create: `src/test/java/com/college_advisor/service/conversation/ConversationStoreTest.java`

- [ ] **Step 1: Write the test**

```java
package com.college_advisor.service.conversation;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests SupabaseConversationStore against a real Supabase DB.
 * Run: ./mvnw test -Dtest=ConversationStoreTest
 */
class ConversationStoreTest {

    private static final String TEST_USER_ID = "00000000-0000-0000-0000-000000000001";

    private static HikariDataSource dataSource;
    private static SupabaseConversationStore store;
    private static JdbcTemplate jdbc;
    private static final List<String> createdConvIds = new ArrayList<>();

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = ConversationStoreTest.class.getClassLoader()
                .getResourceAsStream("application-local.properties")) {
            props.load(in);
        }

        HikariConfig hikari = new HikariConfig();
        hikari.setJdbcUrl(props.getProperty("spring.datasource.url"));
        hikari.setUsername(props.getProperty("spring.datasource.username").strip());
        hikari.setPassword(props.getProperty("spring.datasource.password").strip());
        dataSource = new HikariDataSource(hikari);

        jdbc = new JdbcTemplate(dataSource);
        store = new SupabaseConversationStore(jdbc);

        // Ensure test user exists
        jdbc.update("INSERT INTO users (id) VALUES (?::uuid) ON CONFLICT DO NOTHING", TEST_USER_ID);
    }

    @AfterAll
    static void tearDown() {
        // Clean up test data
        if (jdbc != null && !createdConvIds.isEmpty()) {
            for (String id : createdConvIds) {
                jdbc.update("DELETE FROM messages WHERE conversation_id = ?::uuid", id);
                jdbc.update("DELETE FROM conversations WHERE id = ?::uuid", id);
            }
        }
        if (dataSource != null) dataSource.close();
    }

    @Test
    void createConversationReturnsUuid() {
        String convId = store.createConversation(TEST_USER_ID);
        createdConvIds.add(convId);

        assertNotNull(convId);
        assertFalse(convId.isBlank());
        // UUID format: 8-4-4-4-12
        assertTrue(convId.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"));
    }

    @Test
    void loadHistoryReturnsEmptyForNewConversation() {
        String convId = store.createConversation(TEST_USER_ID);
        createdConvIds.add(convId);

        List<ConversationMessage> history = store.loadHistory(convId);
        assertTrue(history.isEmpty());
    }

    @Test
    void appendAndLoadMessagesInOrder() {
        String convId = store.createConversation(TEST_USER_ID);
        createdConvIds.add(convId);

        store.appendMessage(convId, "user",      "Help me");
        store.appendMessage(convId, "assistant", "What would you like?");
        store.appendMessage(convId, "user",      "Course recommendations");

        List<ConversationMessage> history = store.loadHistory(convId);

        assertEquals(3, history.size());

        assertEquals("user",                    history.get(0).role());
        assertEquals("Help me",                 history.get(0).content());
        assertEquals(0,                          history.get(0).turnIndex());

        assertEquals("assistant",               history.get(1).role());
        assertEquals("What would you like?",    history.get(1).content());
        assertEquals(1,                          history.get(1).turnIndex());

        assertEquals("user",                    history.get(2).role());
        assertEquals("Course recommendations",  history.get(2).content());
        assertEquals(2,                          history.get(2).turnIndex());
    }
}
```

- [ ] **Step 2: Run the test**

```bash
./mvnw test -Dtest=ConversationStoreTest
```

Expected: 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/test/java/com/college_advisor/service/conversation/ConversationStoreTest.java
git commit -m "test: add ConversationStoreTest for Supabase DB operations"
```

---

## Task 5: ConversationService

**Files:**
- Create: `src/main/java/com/college_advisor/service/conversation/ConversationService.java`

- [ ] **Step 1: Create ConversationService**

```java
package com.college_advisor.service.conversation;

import com.college_advisor.service.graph.state.MainState;
import org.bsc.langgraph4j.CompiledGraph;

import java.util.List;
import java.util.Map;

public class ConversationService {

    private final CompiledGraph<MainState> graph;
    private final ConversationStore store;

    public ConversationService(CompiledGraph<MainState> graph, ConversationStore store) {
        this.graph = graph;
        this.store = store;
    }

    /** Creates a new conversation session for a user. Returns the conversation UUID. */
    public String createConversation(String userId) {
        return store.createConversation(userId);
    }

    /**
     * Sends a message in an existing conversation.
     * Loads history from DB, invokes the graph, persists both sides of the exchange.
     */
    public String chat(String userId, String conversationId, String userInput) throws Exception {
        List<ConversationMessage> history = store.loadHistory(conversationId);

        MainState result = graph.invoke(Map.of(
                "userInput",           userInput,
                "userId",              userId,
                "conversationId",      conversationId,
                "conversationHistory", history
        )).get();

        String response = result.response();

        store.appendMessage(conversationId, "user",      userInput);
        store.appendMessage(conversationId, "assistant", response);

        return response;
    }
}
```

- [ ] **Step 2: Build to verify**

```bash
./mvnw clean package -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 3: Commit**

```bash
git add src/main/java/com/college_advisor/service/conversation/ConversationService.java
git commit -m "feat: add ConversationService — wraps graph with DB-backed conversation history"
```

---

## Task 6: RouterClient — history-aware classify

**Files:**
- Modify: `src/main/java/com/college_advisor/service/graph/client/RouterClient.java`

- [ ] **Step 1: Add the overloaded classify method**

In `RouterClient.java`, replace the existing `classify(String userInput)` method and `buildPrompt` with:

```java
/**
 * Classifies userInput (no conversation history).
 */
public String classify(String userInput) {
    return classify(userInput, List.of());
}

/**
 * Classifies userInput with conversation history for context.
 * Falls back to "simple_task" on any error.
 */
public String classify(String userInput, List<com.college_advisor.service.conversation.ConversationMessage> history) {
    try {
        String response = model.chat(buildPrompt(userInput, history));
        return parseRoute(response);
    } catch (Exception e) {
        System.err.println("[RouterClient] classification failed, defaulting to simple_task: " + e.getMessage());
        return "simple_task";
    }
}
```

- [ ] **Step 2: Update buildPrompt to accept history**

Replace the existing `buildPrompt(String userInput)` private method with:

```java
private String buildPrompt(String userInput,
        List<com.college_advisor.service.conversation.ConversationMessage> history) {

    String rules = """
            You are a router for a STAT-major advising assistant at UIUC.
            The student message may be in any language.

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
               Do NOT use if the last assistant message in history was a clarifying
                          question and the user is now answering it — treat the answer
                          as completing the original request and route accordingly.

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

    if (!history.isEmpty()) {
        prompt.append("CONVERSATION HISTORY\n");
        for (com.college_advisor.service.conversation.ConversationMessage m : history) {
            prompt.append(m.role()).append(": ").append(m.content()).append("\n");
        }
        prompt.append("\n");
    }

    prompt.append("QUERY\n\"").append(userInput).append("\"");
    return prompt.toString();
}
```

- [ ] **Step 3: Build to verify**

```bash
./mvnw clean package -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 4: Run existing router tests to confirm no regression**

```bash
./mvnw test -Dtest=RouterLlmTest
```

Expected: all existing parameterized tests PASS (these pass empty history, behaviour unchanged)

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/college_advisor/service/graph/client/RouterClient.java
git commit -m "feat: RouterClient.classify now accepts optional conversation history"
```

---

## Task 7: RouterNode — pass history to classify

**Files:**
- Modify: `src/main/java/com/college_advisor/service/graph/nodes/routerNode/RouterNode.java`

- [ ] **Step 1: Update apply() to pass history**

In `RouterNode.apply()`, replace the line:

```java
decision = client.classify(input);
```

with:

```java
decision = client.classify(input, state.conversationHistory());
```

- [ ] **Step 2: Build to verify**

```bash
./mvnw clean package -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 3: Commit**

```bash
git add src/main/java/com/college_advisor/service/graph/nodes/routerNode/RouterNode.java
git commit -m "feat: RouterNode passes conversation history to RouterClient.classify"
```

---

## Task 8: ClarifyNode — history-aware prompt

**Files:**
- Modify: `src/main/java/com/college_advisor/service/graph/nodes/executionNodes/ClarifyNode/ClarifyNode.java`

- [ ] **Step 1: Add import and update apply()**

Add import at the top:

```java
import com.college_advisor.service.conversation.ConversationMessage;
import java.util.List;
import java.util.stream.Collectors;
```

Replace the `apply()` method body (inside the `if (model == null)` guard) with:

```java
@Override
public Map<String, Object> apply(MainState state) throws Exception {
    System.out.println("[clarify] executing");

    if (model == null) {
        return Map.of("response", "stub: clarify 回复", "nodeHistory", "clarify");
    }

    List<ConversationMessage> history = state.conversationHistory();
    String historyText = history.stream()
            .map(m -> m.role() + ": " + m.content())
            .collect(Collectors.joining("\n"));

    String contextPrefix = historyText.isEmpty()
            ? ""
            : "Conversation history:\n" + historyText + "\n\n";

    String prompt = contextPrefix
            + "The user sent a message that is too vague to answer directly: \""
            + state.userInput() + "\"\n"
            + "Ask them exactly one short clarifying question to understand what they need.\n"
            + "Do not repeat a question already asked in the conversation history.\n"
            + "Do not answer the question. Do not explain yourself. Just ask the question.";

    String response = model.chat(prompt);

    return Map.of(
            "response",    response,
            "nodeHistory", "clarify"
    );
}
```

- [ ] **Step 2: Build to verify**

```bash
./mvnw clean package -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 3: Commit**

```bash
git add src/main/java/com/college_advisor/service/graph/nodes/executionNodes/ClarifyNode/ClarifyNode.java
git commit -m "feat: ClarifyNode prepends conversation history to avoid repeating questions"
```

---

## Task 9: SingleTaskNode + MultiTaskNode — history context

**Files:**
- Modify: `src/main/java/com/college_advisor/service/graph/nodes/executionNodes/PlanNode/SingleTaskNode/SingleTaskNode.java`
- Modify: `src/main/java/com/college_advisor/service/graph/nodes/executionNodes/PlanNode/MultiTaskNode/MultiTaskNode.java`

- [ ] **Step 1: Add helper method and update SingleTaskNode**

In `SingleTaskNode.java`, add these imports:

```java
import com.college_advisor.service.conversation.ConversationMessage;
import java.util.stream.Collectors;
```

Add private helper method at the bottom of the class:

```java
private static String buildContextualInput(String userInput,
        java.util.List<ConversationMessage> history) {
    if (history == null || history.isEmpty()) return userInput;
    String historyText = history.stream()
            .map(m -> m.role() + ": " + m.content())
            .collect(Collectors.joining("\n"));
    return "Conversation history:\n" + historyText + "\n\nCurrent request: " + userInput;
}
```

In `apply()`, replace the two occurrences of `state.userInput()` that are passed to `model.chat(...)` with `buildContextualInput(state.userInput(), state.conversationHistory())`:

**Plan generation call** — change:
```java
UserMessage.from(state.userInput())))
```
to:
```java
UserMessage.from(buildContextualInput(state.userInput(), state.conversationHistory()))))
```

**Preference extraction call** — change:
```java
private UserPreferences extractPreferences(String userInput) {
```
to keep the same signature (it's called with `state.userInput()` — that's intentional, preferences come from the current message only, not history).

- [ ] **Step 2: Apply the same changes to MultiTaskNode**

In `MultiTaskNode.java`, add the same imports and the identical `buildContextualInput` helper, then update the plan generation call in `apply()` the same way:

Change:
```java
UserMessage.from(state.userInput())))
```
to:
```java
UserMessage.from(buildContextualInput(state.userInput(), state.conversationHistory()))))
```

(Leave `extractPreferences(state.userInput())` unchanged — preferences are extracted from the current message only.)

- [ ] **Step 3: Build to verify**

```bash
./mvnw clean package -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add src/main/java/com/college_advisor/service/graph/nodes/executionNodes/PlanNode/SingleTaskNode/SingleTaskNode.java \
        src/main/java/com/college_advisor/service/graph/nodes/executionNodes/PlanNode/MultiTaskNode/MultiTaskNode.java
git commit -m "feat: planning nodes include conversation history when building plans"
```

---

## Task 10: Wire ConversationStore + ConversationService in Spring

**Files:**
- Modify: `src/main/java/com/college_advisor/config/LlmConfig.java`

- [ ] **Step 1: Add the two bean methods to LlmConfig**

Add these imports to `LlmConfig.java`:

```java
import com.college_advisor.service.conversation.ConversationService;
import com.college_advisor.service.conversation.ConversationStore;
import com.college_advisor.service.conversation.SupabaseConversationStore;
```

Add the two bean methods at the bottom of `LlmConfig`:

```java
@Bean
public ConversationStore conversationStore(JdbcTemplate jdbc) {
    return new SupabaseConversationStore(jdbc);
}

@Bean
public ConversationService conversationService(CompiledGraph<MainState> compiledGraph,
                                                ConversationStore conversationStore) {
    return new ConversationService(compiledGraph, conversationStore);
}
```

- [ ] **Step 2: Build and run the Spring context test**

```bash
./mvnw test -Dtest=CollegeAdvisorApplicationTests
```

Expected: PASS — Spring context loads without errors.

- [ ] **Step 3: Commit**

```bash
git add src/main/java/com/college_advisor/config/LlmConfig.java
git commit -m "feat: wire ConversationStore and ConversationService as Spring beans"
```

---

## Task 11: MultiTurnLlmTest — end-to-end two-turn test

**Files:**
- Create: `src/test/java/com/college_advisor/service/conversation/MultiTurnLlmTest.java`

- [ ] **Step 1: Write the test**

```java
package com.college_advisor.service.conversation;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.tools.*;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.InputStream;
import java.util.List;
import java.util.Properties;

import static org.junit.jupiter.api.Assertions.*;

/**
 * End-to-end two-turn test: verifies history is loaded, injected, and persisted correctly.
 * Hits Gemini/DashScope API + Supabase DB.
 * Run: ./mvnw test -Dtest=MultiTurnLlmTest
 */
class MultiTurnLlmTest {

    private static final String TEST_USER_ID = "00000000-0000-0000-0000-000000000001";

    private static HikariDataSource dataSource;
    private static ConversationService service;
    private static SupabaseConversationStore store;
    private static JdbcTemplate jdbc;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = MultiTurnLlmTest.class.getClassLoader()
                .getResourceAsStream("application-local.properties")) {
            props.load(in);
        }

        String apiKey         = props.getProperty("dashscope.api-key");
        String modelName      = props.getProperty("dashscope.model-name");
        String embeddingModel = props.getProperty("dashscope.embedding-model-name");
        String tavilyApiKey   = props.getProperty("tavily.api-key");

        HikariConfig hikari = new HikariConfig();
        hikari.setJdbcUrl(props.getProperty("spring.datasource.url"));
        hikari.setUsername(props.getProperty("spring.datasource.username").strip());
        hikari.setPassword(props.getProperty("spring.datasource.password").strip());
        dataSource = new HikariDataSource(hikari);
        jdbc = new JdbcTemplate(dataSource);

        OpenAiChatModel chatModel = OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(apiKey)
                .modelName(modelName)
                .temperature(0.2)
                .build();

        EmbeddingClient embeddingClient = new EmbeddingClient(apiKey, embeddingModel, 768);
        TavilyClient tavily             = new TavilyClient(tavilyApiKey);
        CourseDataTools courseData      = new CourseDataTools(jdbc, embeddingClient);
        CourseSectionTools sections     = new CourseSectionTools(jdbc);
        GraduationTools graduation      = new GraduationTools(jdbc);
        ProfessorRatingTools profRating = new ProfessorRatingTools(tavily);
        SkillTools skill                = new SkillTools(jdbc);
        RouterClient router             = new RouterClient(apiKey, modelName);

        CompiledGraph<MainState> graph = ParentGraph.build(
                router, chatModel, courseData, sections, graduation, profRating, skill);

        store   = new SupabaseConversationStore(jdbc);
        service = new ConversationService(graph, store);

        // Ensure test user exists
        jdbc.update("INSERT INTO users (id) VALUES (?::uuid) ON CONFLICT DO NOTHING", TEST_USER_ID);
    }

    @AfterAll
    static void tearDown() {
        if (dataSource != null) dataSource.close();
    }

    @Test
    void historyIsPersistedAndLoadedAcrossTurns() throws Exception {
        String convId = service.createConversation(TEST_USER_ID);

        // Turn 1: simple factual question
        String response1 = service.chat(TEST_USER_ID, convId,
                "What are the prerequisites for STAT 400?");
        System.out.println("Turn 1: " + response1);
        assertNotNull(response1);
        assertFalse(response1.isBlank());

        // Verify turn 1 was persisted to DB
        List<ConversationMessage> historyAfterTurn1 = store.loadHistory(convId);
        assertEquals(2, historyAfterTurn1.size());
        assertEquals("user",      historyAfterTurn1.get(0).role());
        assertEquals("assistant", historyAfterTurn1.get(1).role());

        // Turn 2: follow-up using "that course" — history enables correct resolution
        String response2 = service.chat(TEST_USER_ID, convId,
                "Who teaches that course?");
        System.out.println("Turn 2: " + response2);
        assertNotNull(response2);
        assertFalse(response2.isBlank());

        // Verify both turns are in DB
        List<ConversationMessage> historyAfterTurn2 = store.loadHistory(convId);
        assertEquals(4, historyAfterTurn2.size());
    }
}
```

- [ ] **Step 2: Run the test**

```bash
./mvnw test -Dtest=MultiTurnLlmTest
```

Expected: PASS. Turn 2 response should reference STAT 400 (resolving "that course" from history).

- [ ] **Step 3: Commit**

```bash
git add src/test/java/com/college_advisor/service/conversation/MultiTurnLlmTest.java
git commit -m "test: add MultiTurnLlmTest — end-to-end two-turn conversation test"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| DB tables: users, conversations, messages | Task 1 |
| ConversationMessage Java record | Task 2 |
| MainState: conversationId, userId, conversationHistory fields | Task 2 |
| ConversationStore interface | Task 3 |
| SupabaseConversationStore | Task 3 |
| ConversationService wraps graph.invoke() | Task 5 |
| Router: history as string prefix in classify prompt | Task 6 + 7 |
| ClarifyNode: history in prompt | Task 8 |
| SingleTaskNode + MultiTaskNode: history context | Task 9 |
| Spring wiring | Task 10 |
| ReactAgent: unchanged | Not touched ✓ |
| Clarify follow-up handled via Router rule | Task 6 (rule added to prompt) |

All spec requirements covered.

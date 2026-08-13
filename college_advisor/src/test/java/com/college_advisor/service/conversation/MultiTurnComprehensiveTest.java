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
import java.util.Properties;

import static org.junit.jupiter.api.Assertions.*;
import com.college_advisor.service.conversation.UserProfileStore;
import com.college_advisor.service.conversation.SupabaseUserProfileStore;
import com.college_advisor.service.conversation.ProfileExtractor;

/**
 * Comprehensive multi-turn conversation tests covering reference resolution,
 * clarify-to-execution transitions, and pronoun/entity tracking across turns.
 * Hits DashScope API + Supabase DB.
 * Run: ./mvnw test -Dtest=MultiTurnComprehensiveTest
 */
class MultiTurnComprehensiveTest {

    private static final String TEST_USER_ID = "00000000-0000-0000-0000-000000000001";

    private static HikariDataSource dataSource;
    private static ConversationService service;
    private static SupabaseConversationStore store;
    private static JdbcTemplate jdbc;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = MultiTurnComprehensiveTest.class.getClassLoader()
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
        UserProfileStore profileStore = new SupabaseUserProfileStore(jdbc);
        service = new ConversationService(graph, store,
                new DistillationService(store, chatModel),
                new ProfileExtractor(profileStore, chatModel));

        jdbc.update("INSERT INTO users (id) VALUES (?::uuid) ON CONFLICT DO NOTHING", TEST_USER_ID);
    }

    @AfterAll
    static void tearDown() {
        if (dataSource != null) dataSource.close();
    }

    private static long countUserLines(String summary) {
        return summary.lines().filter(l -> l.startsWith("user:")).count();
    }

    /**
     * Scenario 1: Reference resolution across turns (simple_task -> simple_task)
     * Turn 1: ask about STAT 432 prerequisites
     * Turn 2: ask "How many credits is it?" — "it" should resolve to STAT 432
     */
    @Test
    void scenario1_referenceResolutionAcrossTurns() throws Exception {
        String convId = service.createConversation(TEST_USER_ID);

        String response1 = service.chat(TEST_USER_ID, convId,
                "What are the prerequisites for STAT 432?");
        System.out.println("Scenario1 Turn 1: " + response1);
        assertNotNull(response1);
        assertFalse(response1.isBlank(), "Turn 1 response should not be blank");

        String summaryAfter1 = store.loadSummary(TEST_USER_ID, convId);
        assertFalse(summaryAfter1.isBlank(), "Summary should be written after turn 1");
        assertEquals(1, countUserLines(summaryAfter1));

        String response2 = service.chat(TEST_USER_ID, convId,
                "How many credits is it?");
        System.out.println("Scenario1 Turn 2: " + response2);
        assertNotNull(response2);
        assertFalse(response2.isBlank(), "Turn 2 response should not be blank");

        String summaryAfter2 = store.loadSummary(TEST_USER_ID, convId);
        assertEquals(2, countUserLines(summaryAfter2),
                "Summary should contain 2 user turns after turn 2");
    }

    /**
     * Scenario 2: Clarify -> execution
     * Turn 1: vague request -> should trigger clarify
     * Turn 2: detailed follow-up -> should route to build_single_plan and return actual recommendations
     */
    @Test
    void scenario2_clarifyThenExecution() throws Exception {
        String convId = service.createConversation(TEST_USER_ID);

        String response1 = service.chat(TEST_USER_ID, convId,
                "Recommend me some courses");
        System.out.println("Scenario2 Turn 1: " + response1);
        assertNotNull(response1);
        assertFalse(response1.isBlank(), "Turn 1 response should not be blank");

        assertEquals(1, countUserLines(store.loadSummary(TEST_USER_ID, convId)));

        String response2 = service.chat(TEST_USER_ID, convId,
                "I am a junior in STAT, completed STAT 200 and STAT 400, interested in machine learning");
        System.out.println("Scenario2 Turn 2: " + response2);
        assertNotNull(response2);
        assertFalse(response2.isBlank(), "Turn 2 response should not be blank");

        assertEquals(2, countUserLines(store.loadSummary(TEST_USER_ID, convId)));

        // Assert Turn 2 is NOT asking for more info — it should return actual recommendations
        String response2Lower = response2.toLowerCase();
        assertFalse(response2Lower.contains("clarify"),
                "Turn 2 should not ask to clarify again, but got: " + response2);
        assertFalse(response2Lower.contains("could you"),
                "Turn 2 should not ask 'could you', but got: " + response2);
        assertFalse(response2Lower.contains("please provide"),
                "Turn 2 should not say 'please provide', but got: " + response2);
    }

    /**
     * Scenario 3: Multi-turn simple_task chain with entity tracking
     * Turn 1: ask who teaches STAT 107
     * Turn 2: ask about "that professor" on Reddit — should resolve professor from history
     */
    @Test
    void scenario3_multiTurnSimpleTaskChain() throws Exception {
        String convId = service.createConversation(TEST_USER_ID);

        String response1 = service.chat(TEST_USER_ID, convId,
                "Who teaches STAT 107?");
        System.out.println("Scenario3 Turn 1: " + response1);
        assertNotNull(response1);
        assertFalse(response1.isBlank(), "Turn 1 response should not be blank");

        assertEquals(1, countUserLines(store.loadSummary(TEST_USER_ID, convId)));

        String response2 = service.chat(TEST_USER_ID, convId,
                "What do people say about that professor on Reddit?");
        System.out.println("Scenario3 Turn 2: " + response2);
        assertNotNull(response2);
        assertFalse(response2.isBlank(), "Turn 2 response should not be blank");

        assertEquals(2, countUserLines(store.loadSummary(TEST_USER_ID, convId)));
    }

    /**
     * Scenario 4: Follow-up on course info
     * Turn 1: ask if STAT 400 is hard
     * Turn 2: ask "What time does it meet?" — "it" should resolve to STAT 400
     */
    @Test
    void scenario4_followUpOnCourseInfo() throws Exception {
        String convId = service.createConversation(TEST_USER_ID);

        String response1 = service.chat(TEST_USER_ID, convId,
                "Is STAT 400 hard?");
        System.out.println("Scenario4 Turn 1: " + response1);
        assertNotNull(response1);
        assertFalse(response1.isBlank(), "Turn 1 response should not be blank");

        assertEquals(1, countUserLines(store.loadSummary(TEST_USER_ID, convId)));

        String response2 = service.chat(TEST_USER_ID, convId,
                "What time does it meet?");
        System.out.println("Scenario4 Turn 2: " + response2);
        assertNotNull(response2);
        assertFalse(response2.isBlank(), "Turn 2 response should not be blank");

        assertEquals(2, countUserLines(store.loadSummary(TEST_USER_ID, convId)));
    }
}

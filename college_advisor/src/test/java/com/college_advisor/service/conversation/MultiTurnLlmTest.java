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
 * End-to-end two-turn test: verifies summary is persisted and injected correctly.
 * Hits DashScope API + Supabase DB.
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

    @Test
    void summaryIsPersistedAndLoadedAcrossTurns() throws Exception {
        String convId = service.createConversation(TEST_USER_ID);

        // Turn 1: simple factual question
        String response1 = service.chat(TEST_USER_ID, convId,
                "What are the prerequisites for STAT 400?");
        System.out.println("Turn 1: " + response1);
        assertNotNull(response1);
        assertFalse(response1.isBlank());

        // Verify summary written after turn 1
        String summaryAfter1 = store.loadSummary(TEST_USER_ID, convId);
        assertFalse(summaryAfter1.isBlank());
        assertTrue(summaryAfter1.contains("user:"));
        assertTrue(summaryAfter1.contains("assistant:"));

        // Turn 2: follow-up using "that course" — summary enables reference resolution
        String response2 = service.chat(TEST_USER_ID, convId,
                "Who teaches that course?");
        System.out.println("Turn 2: " + response2);
        assertNotNull(response2);
        assertFalse(response2.isBlank());

        // Verify summary contains both turns
        String summaryAfter2 = store.loadSummary(TEST_USER_ID, convId);
        long userCount = summaryAfter2.lines().filter(l -> l.startsWith("user:")).count();
        assertEquals(2, userCount);
    }
}

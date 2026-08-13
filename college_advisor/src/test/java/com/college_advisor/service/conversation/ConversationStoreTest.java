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
        jdbc.update("INSERT INTO users (id) VALUES (?::uuid) ON CONFLICT DO NOTHING", TEST_USER_ID);
    }

    @AfterAll
    static void tearDown() {
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
        assertTrue(convId.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"));
    }

    @Test
    void loadSummaryReturnsEmptyForNewConversation() {
        String convId = store.createConversation(TEST_USER_ID);
        createdConvIds.add(convId);
        assertEquals("", store.loadSummary(TEST_USER_ID, convId));
    }

    @Test
    void updateAndLoadSummaryRoundTrip() {
        String convId = store.createConversation(TEST_USER_ID);
        createdConvIds.add(convId);

        String summary = "user: What are STAT 400 prereqs?\nassistant: STAT 200 and MATH 231.";
        store.updateSummary(TEST_USER_ID, convId, summary);
        assertEquals(summary, store.loadSummary(TEST_USER_ID, convId));
    }

    @Test
    void appendMessageStillWorksForArchival() {
        String convId = store.createConversation(TEST_USER_ID);
        createdConvIds.add(convId);

        store.appendMessage(convId, "user",      "Help me");
        store.appendMessage(convId, "assistant", "What would you like?");

        int count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?::uuid",
                Integer.class, convId);
        assertEquals(2, count);
    }
}

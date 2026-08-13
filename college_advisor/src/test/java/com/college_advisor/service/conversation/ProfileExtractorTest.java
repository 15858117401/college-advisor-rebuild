package com.college_advisor.service.conversation;

import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class ProfileExtractorTest {

    private static final String USER_ID = "user-1";

    static class RecordingProfileStore implements UserProfileStore {
        UserProfile received = null;
        boolean called = false;
        @Override public void mergeProfile(String userId, UserProfile p) {
            called = true;
            received = p;
        }
    }

    static dev.langchain4j.model.chat.ChatModel fixedModel(String reply) {
        return new dev.langchain4j.model.chat.ChatModel() {
            @Override public String chat(String userMessage) { return reply; }
        };
    }

    static String buildLongSummary() {
        String padding = "x".repeat(400);
        StringBuilder sb = new StringBuilder();
        for (int i = 1; i <= 5; i++) {
            sb.append("user: question ").append(i).append(" ").append(padding).append("\n");
            sb.append("assistant: answer ").append(i).append(" ").append(padding).append("\n");
        }
        return sb.toString().strip();
    }

    @Test
    void noOpWhenSummaryBelowThreshold() {
        RecordingProfileStore store = new RecordingProfileStore();
        ProfileExtractor extractor = new ProfileExtractor(store, fixedModel("{}"));
        extractor.extractIfNeeded(USER_ID, "user: hi\nassistant: hello");
        assertFalse(store.called, "should not call mergeProfile for short summary");
    }

    @Test
    void noOpWhenAllFieldsNull() {
        RecordingProfileStore store = new RecordingProfileStore();
        String emptyJson = "{\"year\":null,\"completedCourses\":null,\"preferences\":null,\"schedule\":null}";
        ProfileExtractor extractor = new ProfileExtractor(store, fixedModel(emptyJson));
        extractor.extractIfNeeded(USER_ID, buildLongSummary());
        assertFalse(store.called, "isEmpty() profile must not trigger mergeProfile");
    }

    @Test
    void extractsYearAndCourses() {
        RecordingProfileStore store = new RecordingProfileStore();
        String json = "{\"year\":\"junior\",\"completedCourses\":[\"STAT 400\",\"MATH 241\"]," +
                      "\"preferences\":null,\"schedule\":null}";
        ProfileExtractor extractor = new ProfileExtractor(store, fixedModel(json));
        extractor.extractIfNeeded(USER_ID, buildLongSummary());
        assertTrue(store.called);
        assertEquals("junior", store.received.year());
        assertEquals(List.of("STAT 400", "MATH 241"), store.received.completedCourses());
        assertNull(store.received.preferences());
        assertNull(store.received.schedule());
    }

    @Test
    void extractsSchedule() {
        RecordingProfileStore store = new RecordingProfileStore();
        String json = "{\"year\":null,\"completedCourses\":null,\"preferences\":null," +
                      "\"schedule\":{\"STAT 400\":\"12345\",\"MATH 241\":null}}";
        ProfileExtractor extractor = new ProfileExtractor(store, fixedModel(json));
        extractor.extractIfNeeded(USER_ID, buildLongSummary());
        assertTrue(store.called);
        assertNotNull(store.received.schedule());
        assertEquals("12345", store.received.schedule().get("STAT 400"));
        assertNull(store.received.schedule().get("MATH 241"));
    }

    @Test
    void stripsMarkdownFences() {
        RecordingProfileStore store = new RecordingProfileStore();
        String json = "```json\n{\"year\":\"senior\",\"completedCourses\":null," +
                      "\"preferences\":null,\"schedule\":null}\n```";
        ProfileExtractor extractor = new ProfileExtractor(store, fixedModel(json));
        extractor.extractIfNeeded(USER_ID, buildLongSummary());
        assertTrue(store.called);
        assertEquals("senior", store.received.year());
    }

    @Test
    void silentlySkipsOnLlmFailure() {
        RecordingProfileStore store = new RecordingProfileStore();
        ProfileExtractor extractor = new ProfileExtractor(store,
                new dev.langchain4j.model.chat.ChatModel() {
                    @Override public String chat(String userMessage) {
                        throw new RuntimeException("unavailable");
                    }
                });
        assertDoesNotThrow(() -> extractor.extractIfNeeded(USER_ID, buildLongSummary()));
        assertFalse(store.called);
    }

    @Test
    void silentlySkipsOnJsonParseFailure() {
        RecordingProfileStore store = new RecordingProfileStore();
        ProfileExtractor extractor = new ProfileExtractor(store, fixedModel("not valid json {{{"));
        assertDoesNotThrow(() -> extractor.extractIfNeeded(USER_ID, buildLongSummary()));
        assertFalse(store.called);
    }
}

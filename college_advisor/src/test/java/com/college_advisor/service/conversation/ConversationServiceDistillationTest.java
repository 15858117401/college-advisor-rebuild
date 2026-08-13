package com.college_advisor.service.conversation;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.state.MainState;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import static com.college_advisor.service.conversation.DistillationService.DISTILL_THRESHOLD;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for ConversationService distillation integration.
 * Uses a stub graph (no LLM), fake store, and synchronous executor to eliminate async timing issues.
 * Run: ./mvnw test -Dtest=ConversationServiceDistillationTest
 */
class ConversationServiceDistillationTest {

    private static final String USER_ID = "00000000-0000-0000-0000-000000000001";
    private static final String CONV_ID = "00000000-0000-0000-0000-000000000002";

    private static CompiledGraph<MainState> stubGraph;

    @BeforeAll
    static void setUpGraph() throws Exception {
        // Stub graph — simple_task route, no LLM calls
        stubGraph = ParentGraph.build("simple_task");
    }

    // ── fakes ────────────────────────────────────────────────────────────────

    /** Store that returns a configurable summary and records updateSummary calls */
    static class FakeStore implements ConversationStore {
        private final String summaryToReturn;
        final AtomicBoolean updateCalled   = new AtomicBoolean(false);
        final AtomicReference<String> lastSummary = new AtomicReference<>();

        FakeStore(String summaryToReturn) { this.summaryToReturn = summaryToReturn; }

        @Override public String createConversation(String u) { return CONV_ID; }
        @Override public void appendMessage(String c, String r, String m) {}
        @Override public String loadSummary(String u, String c) { return summaryToReturn; }
        @Override public void updateSummary(String u, String c, String s) {
            updateCalled.set(true);
            lastSummary.set(s);
        }
    }

    /** Records distillIfNeeded calls */
    static class RecordingDistillationService extends DistillationService {
        final AtomicBoolean distillCalled  = new AtomicBoolean(false);
        final AtomicReference<String> receivedSummary = new AtomicReference<>();

        RecordingDistillationService() {
            super(new FakeStore(""), new dev.langchain4j.model.chat.ChatModel() {
                @Override public String chat(String msg) { return "compressed"; }
            });
        }

        @Override
        public void distillIfNeeded(String userId, String conversationId, String summary) {
            distillCalled.set(true);
            receivedSummary.set(summary);
            // Don't call super — we just record, no actual DB write needed here
        }
    }

    static ProfileExtractor noopExtractor() {
        return new ProfileExtractor(
                (uid, p) -> {},
                new dev.langchain4j.model.chat.ChatModel() {
                    @Override public String chat(String userMessage) { return "{}"; }
                });
    }

    // ── tests ────────────────────────────────────────────────────────────────

    @Test
    void distillationFiredAfterChatWhenSummaryLong() throws Exception {
        // Arrange: store returns a summary longer than threshold
        String longSummary = "x".repeat(DISTILL_THRESHOLD + 100);
        FakeStore store = new FakeStore(longSummary);
        RecordingDistillationService recording = new RecordingDistillationService();

        ConversationService service = new ConversationService(
                stubGraph, store, recording, noopExtractor(), Runnable::run); // synchronous executor

        // Act
        service.chat(USER_ID, CONV_ID, "test input");

        // Assert: distillation was triggered and received the updated summary
        assertTrue(recording.distillCalled.get(),
                "distillIfNeeded should be called when summary exceeds threshold");
        assertNotNull(recording.receivedSummary.get());
        // Received summary = newSummary built after this turn
        assertTrue(recording.receivedSummary.get().contains("test input"),
                "distillation receives the updated summary including current turn");
    }

    @Test
    void distillationStillFiredForShortSummary() throws Exception {
        // distillationService.distillIfNeeded is ALWAYS called — it decides internally whether to compress
        FakeStore store = new FakeStore("user: hello\nassistant: hi");
        RecordingDistillationService recording = new RecordingDistillationService();

        ConversationService service = new ConversationService(
                stubGraph, store, recording, noopExtractor(), Runnable::run);

        service.chat(USER_ID, CONV_ID, "test input");

        assertTrue(recording.distillCalled.get(),
                "distillIfNeeded is always called — it handles the threshold check internally");
    }

    @Test
    void updateSummaryCalledBeforeDistillation() throws Exception {
        // Verify that store.updateSummary happens before distillIfNeeded is called
        FakeStore store = new FakeStore("");
        AtomicBoolean summaryWrittenBeforeDistill = new AtomicBoolean(false);

        DistillationService checkingService = new DistillationService(
                store,
                new dev.langchain4j.model.chat.ChatModel() {
                    @Override public String chat(String msg) { return "ok"; }
                }) {
            @Override
            public void distillIfNeeded(String u, String c, String s) {
                // By the time distillIfNeeded runs, store.updateSummary must already have been called
                summaryWrittenBeforeDistill.set(store.updateCalled.get());
            }
        };

        ConversationService service = new ConversationService(
                stubGraph, store, checkingService, noopExtractor(), Runnable::run);

        service.chat(USER_ID, CONV_ID, "input");

        assertTrue(summaryWrittenBeforeDistill.get(),
                "store.updateSummary must be called before distillIfNeeded");
    }
}

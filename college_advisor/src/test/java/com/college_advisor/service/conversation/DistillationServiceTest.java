package com.college_advisor.service.conversation;

import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicReference;

import static com.college_advisor.service.conversation.DistillationService.COMPRESSED_CAP;
import static com.college_advisor.service.conversation.DistillationService.DISTILL_THRESHOLD;
import static org.junit.jupiter.api.Assertions.*;

class DistillationServiceTest {

    private static final String USER_ID = "user-1";
    private static final String CONV_ID = "conv-1";

    // ── fakes ────────────────────────────────────────────────────────────────

    /** Records the last updateSummary call */
    static class RecordingStore implements ConversationStore {
        String updatedSummary = null;
        boolean updateCalled  = false;

        @Override public String createConversation(String userId) { return ""; }
        @Override public void appendMessage(String c, String r, String m) {}
        @Override public String loadSummary(String u, String c) { return ""; }
        @Override public void updateSummary(String u, String c, String summary) {
            updateCalled  = true;
            updatedSummary = summary;
        }
    }

    /** Returns a fixed compressed string */
    static dev.langchain4j.model.chat.ChatModel fixedModel(String reply) {
        return new dev.langchain4j.model.chat.ChatModel() {
            @Override public String chat(String userMessage) { return reply; }
        };
    }

    /** Throws on every call */
    static dev.langchain4j.model.chat.ChatModel failingModel() {
        return new dev.langchain4j.model.chat.ChatModel() {
            @Override public String chat(String userMessage) {
                throw new RuntimeException("LLM unavailable");
            }
        };
    }

    /** Builds a summary with N turns, each padded to ensure total length > threshold */
    static String buildLongSummary(int turns) {
        StringBuilder sb = new StringBuilder();
        String padding = "x".repeat(400); // each turn is ~400+ chars; 5 turns ≈ 4000 > threshold
        for (int i = 1; i <= turns; i++) {
            sb.append("user: question number ").append(i).append(" ").append(padding).append("\n");
            sb.append("assistant: answer number ").append(i).append(" ").append(padding).append("\n");
        }
        return sb.toString().strip();
    }

    // ── tests ────────────────────────────────────────────────────────────────

    @Test
    void noOpWhenSummaryBelowThreshold() {
        RecordingStore store = new RecordingStore();
        DistillationService svc = new DistillationService(store, fixedModel("compressed"));

        String shortSummary = "user: hello\nassistant: hi";
        assertTrue(shortSummary.length() <= DISTILL_THRESHOLD);

        svc.distillIfNeeded(USER_ID, CONV_ID, shortSummary);

        assertFalse(store.updateCalled, "updateSummary should not be called for short summaries");
    }

    @Test
    void noOpWhenOnlyTwoTurnsOrFewer() {
        RecordingStore store = new RecordingStore();
        DistillationService svc = new DistillationService(store, fixedModel("compressed"));

        // 2 turns but padded to exceed threshold
        String padding = "x".repeat(800);
        String twoTurnSummary =
                "user: first question " + padding + "\nassistant: first answer " + padding + "\n" +
                "user: second question " + padding + "\nassistant: second answer " + padding;
        assertTrue(twoTurnSummary.length() > DISTILL_THRESHOLD, "need summary > threshold for this test");

        svc.distillIfNeeded(USER_ID, CONV_ID, twoTurnSummary);

        assertFalse(store.updateCalled, "only 2 turns — nothing to compress, should be no-op");
    }

    @Test
    void compressesOlderTurnsKeepsLast2Raw() {
        RecordingStore store = new RecordingStore();
        String compressedText = "Student asked about STAT 400 prereqs and GPA targets.";
        DistillationService svc = new DistillationService(store, fixedModel(compressedText));

        String summary = buildLongSummary(5); // 5 turns, well above threshold
        assertTrue(summary.length() > DISTILL_THRESHOLD);

        svc.distillIfNeeded(USER_ID, CONV_ID, summary);

        assertTrue(store.updateCalled, "updateSummary should be called");
        String saved = store.updatedSummary;

        // Compressed part is at the top
        assertTrue(saved.startsWith(compressedText),
                "Saved summary should start with compressed text");

        // Last 2 turns raw are preserved at the bottom
        String[] parts = DistillationService.splitSummary(summary);
        String last2Raw = parts[1];
        assertTrue(saved.endsWith(last2Raw.strip()),
                "Saved summary should end with the last 2 raw turns");
    }

    @Test
    void truncatesCompressedPartAtHardCap() {
        RecordingStore store = new RecordingStore();
        // LLM returns a string much longer than COMPRESSED_CAP
        String tooLong = "a".repeat(COMPRESSED_CAP + 500);
        DistillationService svc = new DistillationService(store, fixedModel(tooLong));

        String summary = buildLongSummary(5);
        svc.distillIfNeeded(USER_ID, CONV_ID, summary);

        assertTrue(store.updateCalled);
        String saved = store.updatedSummary;
        // compressed part = first COMPRESSED_CAP chars
        String compressedPart = saved.split("\nuser:")[0];
        assertTrue(compressedPart.length() <= COMPRESSED_CAP,
                "Compressed part must not exceed COMPRESSED_CAP");
    }

    @Test
    void silentlySkipsOnLlmFailure() {
        RecordingStore store = new RecordingStore();
        DistillationService svc = new DistillationService(store, failingModel());

        String summary = buildLongSummary(5);
        assertDoesNotThrow(() -> svc.distillIfNeeded(USER_ID, CONV_ID, summary),
                "LLM failure must not propagate");
        assertFalse(store.updateCalled, "updateSummary must not be called on LLM failure");
    }

    // ── splitSummary unit tests ───────────────────────────────────────────────

    @Test
    void splitSummaryCorrectlySeparatesLast2Turns() {
        String summary =
                "user: turn1\nassistant: resp1\n" +
                "user: turn2\nassistant: resp2\n" +
                "user: turn3\nassistant: resp3\n" +
                "user: turn4\nassistant: resp4";

        String[] parts = DistillationService.splitSummary(summary);
        assertTrue(parts[0].contains("turn1") && parts[0].contains("turn2"),
                "olderPart should contain turns 1 and 2");
        assertTrue(parts[1].contains("turn3") && parts[1].contains("turn4"),
                "last2Turns should contain turns 3 and 4");
        assertFalse(parts[1].contains("turn1"), "turn1 must not leak into last2Turns");
    }

    @Test
    void splitSummaryWithExactly2TurnsReturnsEmptyOlderPart() {
        String summary = "user: q1\nassistant: a1\nuser: q2\nassistant: a2";
        String[] parts = DistillationService.splitSummary(summary);
        assertTrue(parts[0].isEmpty(), "olderPart should be empty for exactly 2 turns");
        assertFalse(parts[1].isEmpty(), "last2Turns should not be empty");
    }
}

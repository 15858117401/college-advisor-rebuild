package com.college_advisor.service.conversation;

import dev.langchain4j.model.chat.ChatModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;

public class DistillationService {

    private static final Logger log = LoggerFactory.getLogger(DistillationService.class);

    static final int DISTILL_THRESHOLD = 3000;  // chars — trigger distillation
    static final int COMPRESSED_CAP    = 2000;  // chars — hard cap on compressed part

    private static final String DISTILL_PROMPT =
            "Compress the following conversation history into a concise summary of at most 3 sentences. " +
            "Preserve key facts: courses mentioned, preferences stated, decisions made. " +
            "Do not add new information. Output only the summary, no preamble.\n\nHISTORY:\n";

    private final ConversationStore store;
    private final ChatModel model;

    public DistillationService(ConversationStore store, ChatModel model) {
        this.store = store;
        this.model = model;
    }

    /**
     * Distills summary if it exceeds DISTILL_THRESHOLD. No-op otherwise.
     * Failures are caught and logged — never propagated to caller.
     */
    public void distillIfNeeded(String userId, String conversationId, String summary) {
        if (summary.length() <= DISTILL_THRESHOLD) return;

        try {
            String[] parts     = splitSummary(summary);
            String olderPart   = parts[0];
            String last2Turns  = parts[1];

            if (olderPart.isEmpty()) return; // only 2 turns exist — nothing to compress

            String compressed = model.chat(DISTILL_PROMPT + olderPart);
            if (compressed.length() > COMPRESSED_CAP) {
                compressed = compressed.substring(0, COMPRESSED_CAP);
            }

            String newSummary = compressed + "\n" + last2Turns;
            store.updateSummary(userId, conversationId, newSummary);
            log.info("[distillation] conv={} compressed {} → {} chars",
                    conversationId, summary.length(), newSummary.length());

        } catch (Exception e) {
            log.warn("[distillation] conv={} failed, skipping: {}", conversationId, e.getMessage());
        }
    }

    /**
     * Splits summary into [olderPart, last2TurnsRaw].
     * Walks backwards to find the 2nd-to-last line starting with "user:" and splits there.
     * Returns ["", fullSummary] when there are ≤2 user turns.
     */
    static String[] splitSummary(String summary) {
        String[] lines = summary.split("\n");
        int userLinesSeen = 0;
        int splitIndex = -1;

        for (int i = lines.length - 1; i >= 0; i--) {
            if (lines[i].startsWith("user:")) {
                userLinesSeen++;
                if (userLinesSeen == 2) {
                    splitIndex = i;
                    break;
                }
            }
        }

        if (splitIndex < 0) {
            // ≤2 user turns — nothing to compress
            return new String[]{"", summary};
        }

        String older    = String.join("\n", Arrays.copyOfRange(lines, 0, splitIndex));
        String last2    = String.join("\n", Arrays.copyOfRange(lines, splitIndex, lines.length));
        return new String[]{older, last2};
    }
}

package com.college_advisor.service.conversation;

import org.springframework.jdbc.core.JdbcTemplate;

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
    public String loadSummary(String userId, String conversationId) {
        return jdbc.queryForObject(
                "SELECT COALESCE(summary, '') FROM conversations WHERE id = ?::uuid AND user_id = ?::uuid",
                String.class, conversationId, userId);
    }

    @Override
    public void updateSummary(String userId, String conversationId, String summary) {
        jdbc.update(
                "UPDATE conversations SET summary = ? WHERE id = ?::uuid AND user_id = ?::uuid",
                summary, conversationId, userId);
    }
}

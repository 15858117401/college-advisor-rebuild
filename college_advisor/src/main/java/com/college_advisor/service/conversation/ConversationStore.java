package com.college_advisor.service.conversation;

public interface ConversationStore {
    String createConversation(String userId);
    void appendMessage(String conversationId, String role, String content);
    String loadSummary(String userId, String conversationId);
    void updateSummary(String userId, String conversationId, String summary);
}

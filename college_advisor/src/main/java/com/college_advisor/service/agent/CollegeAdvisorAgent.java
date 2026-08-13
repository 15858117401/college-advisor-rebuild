package com.college_advisor.service.agent;

import dev.langchain4j.service.UserMessage;

/**
 * Shared langchain4j AiServices interface for all tool-using agents.
 * Each node builds its own instance with its own tool subset and system prompt.
 */
public interface CollegeAdvisorAgent {
    String chat(@UserMessage String userInput);
}

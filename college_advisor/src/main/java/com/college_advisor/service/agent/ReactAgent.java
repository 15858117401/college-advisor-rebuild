package com.college_advisor.service.agent;

import com.college_advisor.service.tools.TerminateTool;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.service.AiServices;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Reusable ReAct agent with built-in error management.
 * Wraps langchain4j AiServices and provides:
 *  - TerminateTool injected automatically so the LLM has an explicit exit point
 *  - Retry with exponential backoff for transient errors (429, 503, timeout)
 *  - ReactResult return type so callers never see raw exceptions
 */
public class ReactAgent {

    private static final int DEFAULT_MAX_TOOL_CALLS = 10;
    private static final int MAX_RETRIES            = 3;

    static final String BASE_SYSTEM_PROMPT = """
            You have access to a set of tools. Use them to retrieve accurate information before answering.
            Call tools when needed. Do not guess or fabricate information.
            If no tool can answer the question, say so clearly.
            When you have a final answer or when no tool can help, call terminate() immediately.
            Do not continue calling other tools after you have reached a conclusion.
            """;

    private final CollegeAdvisorAgent agent;
    private final TerminateTool terminateTool;

    public ReactAgent(ChatModel model, Object... tools) {
        this(model, null, tools);
    }

    public ReactAgent(ChatModel model, String additionalPrompt, Object... tools) {
        this(model, additionalPrompt, DEFAULT_MAX_TOOL_CALLS, tools);
    }

    public ReactAgent(ChatModel model, String additionalPrompt, int maxToolCalls, Object... tools) {
        String systemPrompt = (additionalPrompt == null || additionalPrompt.isBlank())
                ? BASE_SYSTEM_PROMPT
                : BASE_SYSTEM_PROMPT + "\n" + additionalPrompt;

        this.terminateTool = new TerminateTool();
        List<Object> allTools = new ArrayList<>(Arrays.asList(tools));
        allTools.add(this.terminateTool);

        this.agent = AiServices.builder(CollegeAdvisorAgent.class)
                .chatModel(model)
                .tools(allTools)
                .systemMessageProvider(id -> systemPrompt)
                .maxSequentialToolsInvocations(maxToolCalls)
                .build();
    }

    /**
     * Runs the ReAct loop and returns a ReactResult — never throws.
     * Transient errors (rate limit, timeout, service unavailable) are retried up to MAX_RETRIES times.
     * All other errors fail immediately.
     */
    public ReactResult run(String userInput) {
        for (int attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                String result = agent.chat(userInput);
                // If agent.chat() returned "" the LLM put its answer in terminate() instead
                if ((result == null || result.isBlank()) && terminateTool.getCapturedAnswer() != null) {
                    result = terminateTool.getCapturedAnswer();
                }
                return ReactResult.ok(result);
            } catch (Exception e) {
                if (isTransient(e) && attempt < MAX_RETRIES) {
                    System.out.printf("[ReactAgent] transient error (attempt %d/%d): %s%n",
                            attempt + 1, MAX_RETRIES, e.getMessage());
                    try {
                        Thread.sleep(backoffMs(attempt));
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        return ReactResult.fail("INTERRUPTED: " + ie.getMessage(), false);
                    }
                } else {
                    String label = classify(e);
                    System.out.printf("[ReactAgent] %s (attempt %d): %s%n",
                            label, attempt + 1, e.getMessage());
                    return ReactResult.fail(label + ": " + e.getMessage(), isGraphRetryable(label));
                }
            }
        }
        return ReactResult.fail("MAX_RETRIES_EXCEEDED", false);
    }

    /**
     * Whether the graph-level error handler should retry the node.
     * MAX_TOOL_CALLS, AUTH_ERROR, CONTEXT_OVERFLOW are structural — retrying won't help.
     */
    private boolean isGraphRetryable(String label) {
        return switch (label) {
            case "MAX_TOOL_CALLS", "AUTH_ERROR", "CONTEXT_OVERFLOW" -> false;
            default -> true;
        };
    }

    private boolean isTransient(Exception e) {
        String msg = e.getMessage();
        if (msg == null) return false;
        String lower = msg.toLowerCase();
        return lower.contains("429")
                || lower.contains("503")
                || lower.contains("timeout")
                || lower.contains("rate limit")
                || lower.contains("too many requests");
    }

    private String classify(Exception e) {
        String msg = e.getMessage();
        if (msg == null) return "UNKNOWN_ERROR";
        String lower = msg.toLowerCase();
        if (lower.contains("401") || lower.contains("unauthorized")) return "AUTH_ERROR";
        if (lower.contains("429") || lower.contains("rate limit"))   return "RATE_LIMIT";
        if (lower.contains("503") || lower.contains("unavailable"))  return "SERVICE_UNAVAILABLE";
        if (lower.contains("timeout"))                                return "TIMEOUT";
        if (lower.contains("context") || lower.contains("token"))    return "CONTEXT_OVERFLOW";
        if (lower.contains("tool") || lower.contains("invocation"))  return "MAX_TOOL_CALLS";
        return "AGENT_ERROR";
    }

    private long backoffMs(int attempt) {
        return (long) Math.pow(2, attempt) * 1000L;  // 1s, 2s, 4s
    }
}

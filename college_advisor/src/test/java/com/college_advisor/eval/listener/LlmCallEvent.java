package com.college_advisor.eval.listener;

import java.util.List;

/**
 * Immutable snapshot of a single LLM call.
 * No dependency on Braintrust or graph code.
 */
public record LlmCallEvent(
        String       modelName,
        int          promptTokens,
        int          completionTokens,
        int          totalTokens,
        long         latencyMs,
        List<String> toolCalls
) {}

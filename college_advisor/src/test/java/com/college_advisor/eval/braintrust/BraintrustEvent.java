package com.college_advisor.eval.braintrust;

import java.util.List;
import java.util.Map;

/**
 * One row in a Braintrust experiment.
 * No dependency on listener or graph code.
 */
public record BraintrustEvent(
        String              spanId,    // UUID for idempotent upsert
        String              input,     // raw user query
        String              output,    // state.response()
        Map<String, Object> metadata,  // route, nodeHistory, llmCalls breakdown
        Map<String, Object> metrics,   // totalLatencyMs, promptTokens, completionTokens, totalTokens, llmCallCount
        List<String>        tags       // [expectedRoute]
) {}

package com.college_advisor.service.agent;

/**
 * Result returned by ReactAgent.run().
 * success=true  → content holds the LLM's final answer.
 * success=false → error holds a classified error description; retryable indicates
 *                 whether a graph-level retry makes sense.
 */
public record ReactResult(boolean success, String content, String error, boolean retryable) {

    public static ReactResult ok(String content) {
        return new ReactResult(true, content, null, false);
    }

    public static ReactResult fail(String error, boolean retryable) {
        return new ReactResult(false, null, error, retryable);
    }
}

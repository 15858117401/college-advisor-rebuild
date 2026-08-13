package com.college_advisor.eval.listener;

import dev.langchain4j.agent.tool.ToolExecutionRequest;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.model.chat.listener.ChatModelErrorContext;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.chat.listener.ChatModelRequestContext;
import dev.langchain4j.model.chat.listener.ChatModelResponseContext;
import dev.langchain4j.model.output.TokenUsage;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Captures per-call token usage, latency, and tool call names from langchain4j.
 * Thread-safe: safe for concurrent async nodes (planner route).
 * No dependency on Braintrust or graph code.
 */
public class LlmEventListener implements ChatModelListener {

    /** Shared key used to correlate onRequest → onResponse via the attributes map. */
    private static final Object NANOS_KEY = new Object();

    private final CopyOnWriteArrayList<LlmCallEvent> events = new CopyOnWriteArrayList<>();

    @Override
    public void onRequest(ChatModelRequestContext ctx) {
        ctx.attributes().put(NANOS_KEY, System.nanoTime());
    }

    @Override
    public void onResponse(ChatModelResponseContext ctx) {
        long latencyMs = computeLatency(ctx.attributes());

        TokenUsage usage = ctx.chatResponse().tokenUsage();
        int prompt     = usage != null && usage.inputTokenCount()  != null ? usage.inputTokenCount()  : 0;
        int completion = usage != null && usage.outputTokenCount() != null ? usage.outputTokenCount() : 0;
        int total      = usage != null && usage.totalTokenCount()  != null ? usage.totalTokenCount()  : prompt + completion;

        String modelName = ctx.chatResponse().modelName();
        if (modelName == null || modelName.isBlank()) {
            modelName = ctx.modelProvider() != null ? ctx.modelProvider().name() : "unknown";
        }

        List<String> toolCalls = List.of();
        AiMessage aiMsg = ctx.chatResponse().aiMessage();
        if (aiMsg != null && aiMsg.hasToolExecutionRequests()) {
            toolCalls = aiMsg.toolExecutionRequests().stream()
                    .map(ToolExecutionRequest::name)
                    .toList();
        }

        events.add(new LlmCallEvent(modelName, prompt, completion, total, latencyMs, toolCalls));
    }

    @Override
    public void onError(ChatModelErrorContext ctx) {
        long latencyMs = computeLatency(ctx.attributes());
        events.add(new LlmCallEvent("ERROR", 0, 0, 0, latencyMs, List.of()));
    }

    private long computeLatency(Map<Object, Object> attributes) {
        Long startNano = (Long) attributes.get(NANOS_KEY);
        return startNano != null ? (System.nanoTime() - startNano) / 1_000_000L : -1L;
    }

    /** Clears all captured events. Call before each eval case. */
    public void reset() {
        events.clear();
    }

    /** Returns an unmodifiable snapshot of all events since last reset(). */
    public List<LlmCallEvent> snapshot() {
        return Collections.unmodifiableList(new ArrayList<>(events));
    }

    public int totalPromptTokens() {
        return events.stream().mapToInt(LlmCallEvent::promptTokens).sum();
    }

    public int totalCompletionTokens() {
        return events.stream().mapToInt(LlmCallEvent::completionTokens).sum();
    }

    public int totalTokens() {
        return events.stream().mapToInt(LlmCallEvent::totalTokens).sum();
    }

    public long summedCallLatencyMs() {
        return events.stream().mapToLong(LlmCallEvent::latencyMs).filter(l -> l >= 0).sum();
    }
}

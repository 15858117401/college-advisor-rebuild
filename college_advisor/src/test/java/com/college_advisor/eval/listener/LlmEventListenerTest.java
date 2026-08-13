package com.college_advisor.eval.listener;

import dev.langchain4j.agent.tool.ToolExecutionRequest;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.listener.ChatModelErrorContext;
import dev.langchain4j.model.chat.listener.ChatModelRequestContext;
import dev.langchain4j.model.chat.listener.ChatModelResponseContext;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.response.ChatResponse;
import dev.langchain4j.model.output.TokenUsage;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class LlmEventListenerTest {

    /** Fires onRequest then onResponse with the SAME attributes map (as langchain4j does). */
    private void fireRequestResponse(LlmEventListener listener,
                                     int inputTokens, int outputTokens,
                                     String modelName) {
        ChatRequest req = ChatRequest.builder()
                .messages(List.of(UserMessage.from("hello")))
                .build();
        ChatResponse res = ChatResponse.builder()
                .aiMessage(AiMessage.from("hi"))
                .modelName(modelName)
                .tokenUsage(new TokenUsage(inputTokens, outputTokens))
                .build();

        Map<Object, Object> attrs = new HashMap<>();
        listener.onRequest(new ChatModelRequestContext(req, null, attrs));
        listener.onResponse(new ChatModelResponseContext(res, req, null, attrs));
    }

    @Test
    void capturesTokensAndLatency() {
        LlmEventListener listener = new LlmEventListener();
        fireRequestResponse(listener, 100, 50, "qwen-plus");

        List<LlmCallEvent> events = listener.snapshot();
        assertEquals(1, events.size());

        LlmCallEvent e = events.get(0);
        assertEquals("qwen-plus", e.modelName());
        assertEquals(100, e.promptTokens());
        assertEquals(50, e.completionTokens());
        assertEquals(150, e.totalTokens());
        assertTrue(e.latencyMs() >= 0, "latency should be non-negative");
        assertEquals(List.of(), e.toolCalls(), "no tool calls in plain text response");
    }

    @Test
    void resetClearsEvents() {
        LlmEventListener listener = new LlmEventListener();
        fireRequestResponse(listener, 10, 5, "qwen-plus");
        listener.reset();

        assertEquals(0, listener.snapshot().size());
        assertEquals(0, listener.totalTokens());
    }

    @Test
    void aggregatorsSum() {
        LlmEventListener listener = new LlmEventListener();
        fireRequestResponse(listener, 100, 50, "qwen-plus");
        fireRequestResponse(listener, 200, 80, "qwen-plus");

        assertEquals(300, listener.totalPromptTokens());
        assertEquals(130, listener.totalCompletionTokens());
        assertEquals(430, listener.totalTokens());
    }

    @Test
    void nullTokenUsageDefaultsToZero() {
        LlmEventListener listener = new LlmEventListener();

        ChatRequest req = ChatRequest.builder()
                .messages(List.of(UserMessage.from("test")))
                .build();
        ChatResponse res = ChatResponse.builder()
                .aiMessage(AiMessage.from("ok"))
                .modelName("qwen-plus")
                // no tokenUsage set → returns null
                .build();

        Map<Object, Object> attrs = new HashMap<>();
        listener.onRequest(new ChatModelRequestContext(req, null, attrs));
        listener.onResponse(new ChatModelResponseContext(res, req, null, attrs));

        LlmCallEvent e = listener.snapshot().get(0);
        assertEquals(0, e.promptTokens());
        assertEquals(0, e.completionTokens());
        assertEquals(0, e.totalTokens());
    }

    @Test
    void onErrorAfterRequestRecordsNonNegativeLatency() {
        LlmEventListener listener = new LlmEventListener();

        ChatRequest req = ChatRequest.builder()
                .messages(List.of(UserMessage.from("fail")))
                .build();
        Map<Object, Object> attrs = new HashMap<>();
        listener.onRequest(new ChatModelRequestContext(req, null, attrs));
        listener.onError(new ChatModelErrorContext(new RuntimeException("boom"), req, null, attrs));

        assertEquals(1, listener.snapshot().size());
        assertEquals("ERROR", listener.snapshot().get(0).modelName());
        assertTrue(listener.snapshot().get(0).latencyMs() >= 0);
    }

    @Test
    void capturesToolCallNames() {
        LlmEventListener listener = new LlmEventListener();

        ChatRequest req = ChatRequest.builder()
                .messages(List.of(UserMessage.from("search for something")))
                .build();
        AiMessage aiWithTools = AiMessage.from(List.of(
                ToolExecutionRequest.builder().id("1").name("searchCourses").arguments("{}").build(),
                ToolExecutionRequest.builder().id("2").name("filterCourses").arguments("{}").build()
        ));
        ChatResponse res = ChatResponse.builder()
                .aiMessage(aiWithTools)
                .modelName("qwen-plus")
                .tokenUsage(new TokenUsage(50, 10))
                .build();

        Map<Object, Object> attrs = new HashMap<>();
        listener.onRequest(new ChatModelRequestContext(req, null, attrs));
        listener.onResponse(new ChatModelResponseContext(res, req, null, attrs));

        LlmCallEvent e = listener.snapshot().get(0);
        assertEquals(List.of("searchCourses", "filterCourses"), e.toolCalls());
    }

    @Test
    void onErrorWithoutPrecedingRequestRecordsNegativeOneLatency() {
        LlmEventListener listener = new LlmEventListener();

        ChatRequest req = ChatRequest.builder()
                .messages(List.of(UserMessage.from("fail")))
                .build();
        Map<Object, Object> attrs = new HashMap<>();
        // Note: onRequest is NOT called — no NANOS_KEY in attrs
        listener.onError(new ChatModelErrorContext(new RuntimeException("boom"), req, null, attrs));

        assertEquals(1, listener.snapshot().size());
        assertEquals("ERROR", listener.snapshot().get(0).modelName());
        assertEquals(-1L, listener.snapshot().get(0).latencyMs());
    }
}

package com.college_advisor.service.conversation;

import com.college_advisor.service.graph.state.MainState;
import org.bsc.langgraph4j.CompiledGraph;

import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.concurrent.ForkJoinPool;

public class ConversationService {

    private final CompiledGraph<MainState> graph;
    private final ConversationStore store;
    private final DistillationService distillation;
    private final ProfileExtractor profileExtractor;
    private final Executor executor;

    /** Production constructor */
    public ConversationService(CompiledGraph<MainState> graph,
                               ConversationStore store,
                               DistillationService distillation,
                               ProfileExtractor profileExtractor) {
        this(graph, store, distillation, profileExtractor, ForkJoinPool.commonPool());
    }

    /** Test constructor — accepts a custom executor (e.g. Runnable::run for synchronous execution) */
    ConversationService(CompiledGraph<MainState> graph,
                        ConversationStore store,
                        DistillationService distillation,
                        ProfileExtractor profileExtractor,
                        Executor executor) {
        this.graph            = graph;
        this.store            = store;
        this.distillation     = distillation;
        this.profileExtractor = profileExtractor;
        this.executor         = executor;
    }

    public String createConversation(String userId) {
        return store.createConversation(userId);
    }

    public String chat(String userId, String conversationId, String userInput) throws Exception {
        String summary = store.loadSummary(userId, conversationId);

        MainState result = graph.invoke(Map.of(
                "userInput",           userInput,
                "userId",              userId,
                "conversationId",      conversationId,
                "conversationSummary", summary
        )).get();

        String response = result.response();

        store.appendMessage(conversationId, "user",      userInput);
        store.appendMessage(conversationId, "assistant", response);

        String newSummary = summary.isEmpty()
                ? "user: " + userInput + "\nassistant: " + response
                : summary + "\nuser: " + userInput + "\nassistant: " + response;
        store.updateSummary(userId, conversationId, newSummary);

        // Fire-and-forget: both run concurrently, neither blocks the response
        CompletableFuture.runAsync(
                () -> distillation.distillIfNeeded(userId, conversationId, newSummary), executor);
        CompletableFuture.runAsync(
                () -> profileExtractor.extractIfNeeded(userId, newSummary), executor);

        return response;
    }
}

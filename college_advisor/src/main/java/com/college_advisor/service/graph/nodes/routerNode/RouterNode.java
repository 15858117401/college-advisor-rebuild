package com.college_advisor.service.graph.nodes.routerNode;

import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.Map;

public class RouterNode implements NodeAction<MainState> {

    // ── stub mode ─────────────────────────────────────────────────────────
    private final String fixedRoute;        // null in LLM mode

    // ── LLM mode ──────────────────────────────────────────────────────────
    private final RouterClient client; // null in stub mode

    /** Default stub constructor — preserves existing no-arg behaviour */
    public RouterNode() {
        this("simple_task");
    }

    /** Stub constructor — used by tests via ParentGraph.build(String forceRoute) */
    public RouterNode(String fixedRoute) {
        this.fixedRoute = fixedRoute;
        this.client     = null;
    }

    /** LLM constructor — used in production via LlmConfig */
    public RouterNode(RouterClient client) {
        this.client     = client;
        this.fixedRoute = null;
    }

    @Override
    public Map<String, Object> apply(MainState state) throws Exception {
        System.out.println("[router] executing");

        String decision;
        if (client != null) {
            String input = state.userInput();
            System.out.println("[router] classifying input: " + input);
            decision = client.classify(input, state.conversationSummary());
            System.out.println("[router] classified as: " + decision);
        } else {
            decision = fixedRoute;
        }

        return Map.of("routeDecision", decision, "nodeHistory", "router");
    }

    public String route(MainState state) throws Exception {
        if (state.currentError() != null) return "error_handler";
        return state.routeDecision();
    }
}

package com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.error;

import com.college_advisor.service.graph.state.ErrorState.ErrorContext;
import com.college_advisor.service.graph.state.ErrorState.ErrorInfo;
import com.college_advisor.service.graph.state.SubgraphState;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.HashMap;
import java.util.Map;

public class SubgraphErrorHandlerNode implements NodeAction<SubgraphState> {

    private static final int MAX_RETRIES = 3;

    @Override
    public Map<String, Object> apply(SubgraphState state) throws Exception {
        System.out.println("[subgraph_error_handler] executing");

        ErrorContext ctx = state.errorContext();
        ErrorInfo err = ctx.currentError();

        if (err == null) {
            return Map.of("errorContext", new ErrorContext(null, ctx.nodeRetries(), "subgraph_output"),
                          "nodeHistory",  "subgraph_error_handler");
        }

        int retries = ctx.nodeRetries().getOrDefault(err.sourceNode, 0);

        if (!err.retryable || retries >= MAX_RETRIES) {
            System.out.println("[subgraph_error_handler] → subgraph_fatal_error (retryable=" + err.retryable + ", retries=" + retries + ")");
            return Map.of("errorContext", new ErrorContext(err, ctx.nodeRetries(), "subgraph_fatal_error"),
                          "nodeHistory",  "subgraph_error_handler");
        }

        Map<String, Integer> updated = new HashMap<>(ctx.nodeRetries());
        updated.put(err.sourceNode, retries + 1);
        System.out.println("[subgraph_error_handler] → retry " + err.sourceNode + " (attempt " + (retries + 1) + "/" + MAX_RETRIES + ")");
        return Map.of("errorContext", new ErrorContext(err, updated, err.sourceNode),
                      "nodeHistory",  "subgraph_error_handler");
    }

    public String route(SubgraphState state) {
        return state.errorContext().errorDecision();
    }
}

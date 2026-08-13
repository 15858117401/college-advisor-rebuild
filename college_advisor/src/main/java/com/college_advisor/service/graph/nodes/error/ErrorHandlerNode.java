package com.college_advisor.service.graph.nodes.error;

import com.college_advisor.service.graph.state.ErrorState.ErrorContext;
import com.college_advisor.service.graph.state.ErrorState.ErrorInfo;
import com.college_advisor.service.graph.state.MainState;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.HashMap;
import java.util.Map;

public class ErrorHandlerNode implements NodeAction<MainState> {

    private static final int MAX_RETRIES = 3;

    @Override
    public Map<String, Object> apply(MainState state) throws Exception {
        System.out.println("[error_handler] executing");

        ErrorContext ctx = state.errorContext();
        ErrorInfo err = ctx.currentError();

        if (err == null) {
            // 不应该到这里，保险降级
            return Map.of("errorContext", new ErrorContext(null, ctx.nodeRetries(), "output"));
        }

        int retries = ctx.nodeRetries().getOrDefault(err.sourceNode, 0);

        if (!err.retryable || retries >= MAX_RETRIES) {
            System.out.println("[error_handler] → fatal_error (retryable=" + err.retryable + ", retries=" + retries + ")");
            return Map.of("errorContext", new ErrorContext(err, ctx.nodeRetries(), "fatal_error"), "nodeHistory", "error_handler");
        }

        Map<String, Integer> updatedRetries = new HashMap<>(ctx.nodeRetries());
        updatedRetries.put(err.sourceNode, retries + 1);
        System.out.println("[error_handler] → retry " + err.sourceNode + " (attempt " + (retries + 1) + "/" + MAX_RETRIES + ")");
        return Map.of("errorContext", new ErrorContext(err, updatedRetries, err.sourceNode), "nodeHistory", "error_handler");
    }

    public String route(MainState state) throws Exception {
        return state.errorContext().errorDecision();
    }
}

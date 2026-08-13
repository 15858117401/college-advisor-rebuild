package com.college_advisor.service.graph.nodes;

import com.college_advisor.service.graph.state.MainState;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.Map;

public class OutputNode implements NodeAction<MainState> {

    @Override
    public Map<String, Object> apply(MainState state) throws Exception {
        System.out.println("[output] >>> " + state.response());
        return Map.of("nodeHistory", "output");
    }
}

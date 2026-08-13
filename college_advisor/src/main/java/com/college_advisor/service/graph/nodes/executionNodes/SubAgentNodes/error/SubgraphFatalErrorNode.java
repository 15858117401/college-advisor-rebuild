package com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.error;

import com.college_advisor.service.graph.state.SubgraphState;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.Map;

public class SubgraphFatalErrorNode implements NodeAction<SubgraphState> {

    @Override
    public Map<String, Object> apply(SubgraphState state) throws Exception {
        System.out.println("[subgraph_fatal_error] " + state.errorContext().currentError());
        return Map.of("nodeHistory", "subgraph_fatal_error");
    }
}

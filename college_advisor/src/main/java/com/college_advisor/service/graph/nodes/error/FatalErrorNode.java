package com.college_advisor.service.graph.nodes.error;

import com.college_advisor.service.graph.state.MainState;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.Map;

public class FatalErrorNode implements NodeAction<MainState> {

    @Override
    public Map<String, Object> apply(MainState state) throws Exception {
        System.out.println("[fatal_error] " + state.errorContext().currentError());
        return Map.of("response", "抱歉，系统出现了问题，请稍后重试。", "nodeHistory", "fatal_error");
    }
}

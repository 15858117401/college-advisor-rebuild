package com.college_advisor;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.state.MainState;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 不启动 Spring 上下文，直接跑图的骨架验收测试。
 */
class GraphSkeletonTest {

    private MainState run(String routeDecision) throws Exception {
        var graph = ParentGraph.build(routeDecision);
        return graph.invoke(Map.of("userInput", "test input")).get();
    }

    @Test
    void test_reactAgent_path() throws Exception {
        MainState state = run("simple_task");
        assertTrue(state.response().contains("simple_task"), "response 应来自 simple_task");
    }

    @Test
    void test_planner_path() throws Exception {
        MainState state = run("planner");
        assertFalse(state.response().isBlank(), "planner 应该有 response");
    }

    @Test
    void test_buildSinglePlan_path() throws Exception {
        MainState state = run("build_single_plan");
        assertFalse(state.response().isBlank(), "build_single_plan 应该有 response");
    }

    @Test
    void test_clarify_path() throws Exception {
        MainState state = run("clarify");
        assertFalse(state.response().isEmpty(), "clarify 应该有 response");
    }
}

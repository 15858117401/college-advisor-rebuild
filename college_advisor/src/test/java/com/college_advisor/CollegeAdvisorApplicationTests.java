package com.college_advisor;

import com.college_advisor.service.graph.state.MainState;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

@SpringBootTest
@ActiveProfiles("local")
class CollegeAdvisorApplicationTests {

    @Autowired
    CompiledGraph<MainState> graph;

    @Test
    void contextLoads() {
    }

    private MainState ask(String input) throws Exception {
        MainState state = graph.invoke(Map.of("userInput", input)).get();
        System.out.println("Q: " + input);
        System.out.println("A: " + state.response());
        System.out.println("---");
        return state;
    }

    private void assertNonEmpty(MainState state) {
        assertNotNull(state.response());
        assertFalse(state.response().isBlank());
    }

    @ParameterizedTest(name = "[simple_task] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.router.RouterLlmTest#simpleTaskInputs")
    void simpleTask(String input) throws Exception {
        assertNonEmpty(ask(input));
    }

    @ParameterizedTest(name = "[clarify] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.router.RouterLlmTest#clarifyInputs")
    void clarify(String input) throws Exception {
        assertNonEmpty(ask(input));
    }

    @ParameterizedTest(name = "[build_single_plan] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.router.RouterLlmTest#buildSinglePlanInputs")
    void buildSinglePlan(String input) throws Exception {
        assertNonEmpty(ask(input));
    }

    @ParameterizedTest(name = "[planner] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.router.RouterLlmTest#plannerInputs")
    void planner(String input) throws Exception {
        assertNonEmpty(ask(input));
    }
}

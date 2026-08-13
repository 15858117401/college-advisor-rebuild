package com.college_advisor.service.Nodes.PlanNode;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.graph.state.Plan;
import com.college_advisor.service.graph.state.PlanTask;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.io.InputStream;
import java.util.Map;
import java.util.Properties;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 全链路测试 SingleTaskNode：真实 LLM 路由 → 真实 plan 生成 → stop（stub subgraph，不需要 DB）。
 * 测试案例复用 RouterLlmTest#buildSinglePlanInputs。
 *
 * 运行：./mvnw test -Dtest=BuildSinglePlanLlmTest
 */
class BuildSinglePlanLlmTest {

    private static final Set<String> VALID_TASK_TYPES =
            Set.of("recommender", "scheduler", "course_planner");

    private static CompiledGraph<MainState> graph;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = BuildSinglePlanLlmTest.class.getClassLoader()
                .getResourceAsStream("application-local.properties")) {
            props.load(in);
        }

        String apiKey    = props.getProperty("dashscope.api-key");
        String modelName = props.getProperty("dashscope.model-name");

        OpenAiChatModel chatModel = OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(apiKey)
                .modelName(modelName)
                .temperature(0.2)
                .build();

        // 真实 router + 真实 SingleTaskNode；ExecutionSubgraph 为 stub，不需要 DB
        graph = ParentGraph.build(new RouterClient(apiKey, modelName), chatModel);
    }

    @ParameterizedTest(name = "[build_single_plan] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.router.RouterLlmTest#buildSinglePlanInputs")
    void shouldProduceValidPlan(String userInput) throws Exception {
        MainState state = graph.invoke(Map.of("userInput", userInput)).get();

        Plan plan = state.taskContext().plan();
        assertNotNull(plan, "plan should not be null");
        assertEquals(1, plan.chains().size(), "single plan should have exactly 1 chain");
        assertEquals(1, plan.chains().get(0).size(), "single plan chain should have exactly 1 task");

        PlanTask task = plan.chains().get(0).get(0);
        assertEquals("t1", task.id());
        assertTrue(VALID_TASK_TYPES.contains(task.taskType()),
                "taskType should be recommender/scheduler/course_planner, got: " + task.taskType());
        assertFalse(task.goal().isBlank(), "goal should not be blank");

        System.out.println("Q:           " + userInput);
        System.out.println("taskType:    " + task.taskType());
        System.out.println("goal:        " + task.goal());
        System.out.println("constraints: " + task.constraints());
        System.out.println("---");
    }
}

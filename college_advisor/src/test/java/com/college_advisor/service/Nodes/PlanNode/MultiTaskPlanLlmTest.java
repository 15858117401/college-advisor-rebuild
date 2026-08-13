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
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 全链路测试 MultiTaskNode：真实 LLM 路由 → 真实 plan 生成 → stop（stub subgraph，不需要 DB）。
 * 测试案例复用 RouterLlmTest#plannerInputs。
 *
 * 运行：./mvnw test -Dtest=MultiTaskPlanLlmTest
 */
class MultiTaskPlanLlmTest {

    private static final Set<String> VALID_TASK_TYPES =
            Set.of("recommender", "scheduler", "course_planner");

    private static CompiledGraph<MainState> graph;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = MultiTaskPlanLlmTest.class.getClassLoader()
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

        // 真实 router + 真实 MultiTaskNode；ExecutionSubgraph 为 stub，不需要 DB
        graph = ParentGraph.build(new RouterClient(apiKey, modelName), chatModel);
    }

    @ParameterizedTest(name = "[planner] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.router.RouterLlmTest#plannerInputs")
    void shouldProduceValidMultiTaskPlan(String userInput) throws Exception {
        MainState state = graph.invoke(Map.of("userInput", userInput)).get();

        Plan plan = state.taskContext().plan();
        assertNotNull(plan, "plan should not be null");
        assertFalse(plan.chains().isEmpty(), "plan should have at least 1 chain");

        // 统计总任务数，planner 应产生 2 个或以上
        long totalTasks = plan.chains().stream().mapToLong(List::size).sum();
        assertTrue(totalTasks >= 2,
                "planner plan should have at least 2 tasks total, got: " + totalTasks);

        // 每个任务的 id、taskType、goal 都必须合法
        for (List<PlanTask> chain : plan.chains()) {
            assertFalse(chain.isEmpty(), "each chain should have at least 1 task");
            for (PlanTask task : chain) {
                assertNotNull(task.id(), "task id should not be null");
                assertFalse(task.id().isBlank(), "task id should not be blank");
                assertTrue(VALID_TASK_TYPES.contains(task.taskType()),
                        "taskType should be recommender/scheduler/course_planner, got: " + task.taskType());
                assertFalse(task.goal().isBlank(), "task goal should not be blank");
            }
        }

        System.out.println("Q: " + userInput);
        System.out.println("chains: " + plan.chains().size() + ", total tasks: " + totalTasks);
        for (int i = 0; i < plan.chains().size(); i++) {
            System.out.println("  chain[" + i + "]:");
            for (PlanTask t : plan.chains().get(i)) {
                System.out.println("    [" + t.id() + "] " + t.taskType() + " — " + t.goal());
                if (!t.constraints().isEmpty()) {
                    System.out.println("    constraints: " + t.constraints());
                }
            }
        }
        System.out.println("---");
    }
}

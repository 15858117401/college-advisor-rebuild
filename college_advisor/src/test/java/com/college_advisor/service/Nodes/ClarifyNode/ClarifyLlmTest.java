package com.college_advisor.service.Nodes.ClarifyNode;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.io.InputStream;
import java.util.Map;
import java.util.Properties;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * 全链路测试：真实 Router → clarify → ClarifyNode（langchain4j ChatModel，无 DB）。
 * 测试用例复用 ClarifyNodeLlmTest.clarifyInputs()。
 *
 * 运行：./mvnw test -Dtest=ClarifyLlmTest
 */
class ClarifyLlmTest {

    private static CompiledGraph<MainState> graph;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = ClarifyLlmTest.class.getClassLoader()
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

        graph = ParentGraph.build(
                new RouterClient(apiKey, modelName),
                chatModel
        );
    }

    @ParameterizedTest(name = "[full pipeline] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.ClarifyNode.ClarifyNodeLlmTest#clarifyInputs")
    void shouldProduceNonEmptyResponse(String input) throws Exception {
        MainState state = graph.invoke(Map.of("userInput", input)).get();
        System.out.println("Q: " + input);
        System.out.println("A: " + state.response());
        System.out.println("---");
        assertNotNull(state.response());
        assertFalse(state.response().isBlank());
    }
}

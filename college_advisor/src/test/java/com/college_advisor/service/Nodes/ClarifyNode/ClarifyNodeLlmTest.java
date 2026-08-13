package com.college_advisor.service.Nodes.ClarifyNode;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.state.MainState;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.io.InputStream;
import java.util.Map;
import java.util.Properties;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * 跳过 Router（强制路由到 clarify），直接测试 ClarifyNode（langchain4j ChatModel，无 DB）。
 *
 * 运行：./mvnw test -Dtest=ClarifyNodeLlmTest
 */
class ClarifyNodeLlmTest {

    private static CompiledGraph<MainState> graph;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = ClarifyNodeLlmTest.class.getClassLoader()
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

        graph = ParentGraph.build("clarify", chatModel);
    }

    /** Mirrors the clarify inputs in RouterLlmTest#shouldRouteToClarify. */
    static Stream<String> clarifyInputs() {
        return Stream.of(
                "Help me",
                "Whatever you think is best",
                "You decide for me",
                "I don't know",
                "Anything is fine",
                "Can you help me",
                "I have a question",
                "I want to learn",
                "Look something up for me"
        );
    }

    @ParameterizedTest(name = "[clarify] \"{0}\"")
    @MethodSource("clarifyInputs")
    void shouldProduceNonEmptyResponse(String input) throws Exception {
        MainState state = graph.invoke(Map.of("userInput", input)).get();
        System.out.println("Q: " + input);
        System.out.println("A: " + state.response());
        System.out.println("---");
        assertNotNull(state.response());
        assertFalse(state.response().isBlank());
    }
}

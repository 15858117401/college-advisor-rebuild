package com.college_advisor.service.Nodes.SimpleTaskNode;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.tools.CourseDataTools;
import com.college_advisor.service.tools.CourseSectionTools;
import com.college_advisor.service.tools.GraduationTools;
import com.college_advisor.service.tools.ProfessorRatingTools;
import com.college_advisor.service.tools.TavilyClient;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.InputStream;
import java.util.Map;
import java.util.Properties;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * 跳过 Router（强制路由到 simple_task），直接测试 langchain4j AiServices 循环。
 * 使用真实 ChatModel + 真实 domain tools（连 Supabase DB）。
 *
 * 运行：./mvnw test -Dtest=SimpleTaskMockedRouterTest
 */
class SimpleTaskMockedRouterTest {

    private static HikariDataSource dataSource;
    private static CompiledGraph<MainState> graph;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = SimpleTaskMockedRouterTest.class.getClassLoader()
                .getResourceAsStream("application-local.properties")) {
            props.load(in);
        }

        String apiKey         = props.getProperty("dashscope.api-key");
        String modelName      = props.getProperty("dashscope.model-name");
        String embeddingModel = props.getProperty("dashscope.embedding-model-name");
        String tavilyApiKey   = props.getProperty("tavily.api-key");

        HikariConfig hikari = new HikariConfig();
        hikari.setJdbcUrl(props.getProperty("spring.datasource.url"));
        hikari.setUsername(props.getProperty("spring.datasource.username").strip());
        hikari.setPassword(props.getProperty("spring.datasource.password").strip());
        dataSource = new HikariDataSource(hikari);

        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        EmbeddingClient embeddingClient = new EmbeddingClient(apiKey, embeddingModel, 768);
        TavilyClient tavily = new TavilyClient(tavilyApiKey);

        OpenAiChatModel chatModel = OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(apiKey)
                .modelName(modelName)
                .temperature(0.2)
                .build();

        CourseDataTools courseData = new CourseDataTools(jdbc, embeddingClient);
        CourseSectionTools sections = new CourseSectionTools(jdbc);
        GraduationTools graduation = new GraduationTools(jdbc);
        ProfessorRatingTools profRating = new ProfessorRatingTools(tavily);

        // 强制路由到 simple_task，跳过 LLM router
        graph = ParentGraph.build("simple_task", chatModel, courseData, sections, graduation, profRating);
    }

    @AfterAll
    static void tearDown() {
        if (dataSource != null) dataSource.close();
    }

    private MainState ask(String userInput) throws Exception {
        return graph.invoke(Map.of("userInput", userInput)).get();
    }

    @ParameterizedTest(name = "[simple_task] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.router.RouterLlmTest#simpleTaskInputs")
    void shouldProduceNonEmptyResponse(String input) throws Exception {
        MainState state = ask(input);
        assertNotNull(state.response(), "response 不应为 null");
        assertFalse(state.response().isBlank(), "response 不应为空");
        System.out.println("Q: " + input);
        System.out.println("A: " + state.response());
        System.out.println("---");
    }
}

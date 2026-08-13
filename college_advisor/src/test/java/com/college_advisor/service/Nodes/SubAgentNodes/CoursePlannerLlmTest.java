package com.college_advisor.service.Nodes.SubAgentNodes;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.tools.*;
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
 * Full pipeline test: real Router → build_single_plan → SingleTaskNode → ExecutionSubgraph → CoursePlannerNode.
 * Uses degree planning inputs from RouterLlmTest#coursePlannerInputs — no forced routing.
 *
 * Run: ./mvnw test -Dtest=CoursePlannerLlmTest
 */
class CoursePlannerLlmTest {

    private static HikariDataSource dataSource;
    private static CompiledGraph<MainState> graph;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = CoursePlannerLlmTest.class.getClassLoader()
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

        JdbcTemplate jdbc            = new JdbcTemplate(dataSource);
        EmbeddingClient embed  = new EmbeddingClient(apiKey, embeddingModel, 768);
        TavilyClient tavily          = new TavilyClient(tavilyApiKey);

        OpenAiChatModel chatModel = OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(apiKey).modelName(modelName).temperature(0.2).build();

        graph = ParentGraph.build(
                new RouterClient(apiKey, modelName),
                chatModel,
                new CourseDataTools(jdbc, embed),
                new CourseSectionTools(jdbc),
                new GraduationTools(jdbc),
                new ProfessorRatingTools(tavily),
                new SkillTools(jdbc));
    }

    @AfterAll
    static void tearDown() {
        if (dataSource != null) dataSource.close();
    }

    @ParameterizedTest(name = "[course_planner full pipeline] \"{0}\"")
    @MethodSource("com.college_advisor.service.Nodes.router.RouterLlmTest#coursePlannerInputs")
    void shouldProducePlan(String input) throws Exception {
        MainState state = graph.invoke(Map.of("userInput", input)).get();
        System.out.println("Q: " + input);
        System.out.println("A: " + state.response());
        System.out.println("---");
        assertNotNull(state.response());
        assertFalse(state.response().isBlank());
    }
}

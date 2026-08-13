package com.college_advisor.service.Nodes.SubAgentNodes;

import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.tools.CourseDataTools;
import com.college_advisor.service.tools.CourseSectionTools;
import com.college_advisor.service.tools.GraduationTools;
import com.college_advisor.service.tools.ProfessorRatingTools;
import com.college_advisor.service.tools.SkillTools;
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
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * 全链路测试：真实 Router → build_single_plan → SingleTaskNode → ExecutionSubgraph → RecommenderNode。
 * 使用 buildSinglePlanInputs 中纯推荐类的 case，验证完整 pipeline 包括 router 分类、plan 生成、RecommenderNode 执行。
 *
 * 运行：./mvnw test -Dtest=RecommenderSingleTaskLlmTest
 */
class RecommenderSingleTaskLlmTest {

    private static HikariDataSource dataSource;
    private static CompiledGraph<MainState> graph;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = RecommenderSingleTaskLlmTest.class.getClassLoader()
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

        CourseDataTools courseData       = new CourseDataTools(jdbc, embeddingClient);
        CourseSectionTools sections      = new CourseSectionTools(jdbc);
        GraduationTools graduation       = new GraduationTools(jdbc);
        ProfessorRatingTools profRating  = new ProfessorRatingTools(tavily);
        SkillTools skill                 = new SkillTools(jdbc);

        graph = ParentGraph.build(
                new RouterClient(apiKey, modelName),
                chatModel,
                courseData,
                sections,
                graduation,
                profRating,
                skill);
    }

    @AfterAll
    static void tearDown() {
        if (dataSource != null) dataSource.close();
    }

    static Stream<String> recommenderInputs() {
        return Stream.of(
                "I am a sophomore in the STAT major and I have completed STAT 100 and STAT 200. Recommend me 3 courses for next semester.",
                "I want to study data science. I am a junior in the STAT major and have already taken STAT 107 and STAT 200. Recommend me some courses.",
                "I am a junior in the STAT major and I have finished STAT 400. I am interested in probability theory. What courses do you recommend I take next?",
                "I want to go to grad school in statistics. I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. What courses should I prioritize?",
                "I am a sophomore in the STAT major with a 3.4 GPA and have completed STAT 200. Recommend me courses that are manageable so I can make the Dean's List."
        );
    }

    private MainState ask(String userInput) throws Exception {
        MainState state = graph.invoke(Map.of("userInput", userInput)).get();
        System.out.println("Q: " + userInput);
        System.out.println("A: " + state.response());
        System.out.println("---");
        return state;
    }

    @ParameterizedTest(name = "[recommender full pipeline] \"{0}\"")
    @MethodSource("recommenderInputs")
    void shouldProduceNonEmptyRecommendation(String input) throws Exception {
        MainState state = ask(input);
        assertNotNull(state.response(), "response 不应为 null");
        assertFalse(state.response().isBlank(), "response 不应为空");
    }
}

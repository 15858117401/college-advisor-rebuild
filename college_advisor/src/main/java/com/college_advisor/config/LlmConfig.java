package com.college_advisor.config;

import com.college_advisor.service.conversation.ConversationService;
import com.college_advisor.service.conversation.ConversationStore;
import com.college_advisor.service.conversation.DistillationService;
import com.college_advisor.service.conversation.ProfileExtractor;
import com.college_advisor.service.conversation.SupabaseConversationStore;
import com.college_advisor.service.conversation.SupabaseUserProfileStore;
import com.college_advisor.service.conversation.UserProfileStore;
import com.college_advisor.service.graph.ParentGraph;
import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.tools.*;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

@Configuration
public class LlmConfig {

    @Value("${dashscope.api-key}")
    private String apiKey;

    @Value("${dashscope.model-name}")
    private String modelName;

    @Value("${tavily.api-key}")
    private String tavilyApiKey;

    @Bean
    public RouterClient routerClient() {
        return new RouterClient(apiKey, modelName);
    }

    @Bean
    public EmbeddingClient embeddingClient(
            @Value("${dashscope.api-key}") String apiKey,
            @Value("${dashscope.embedding-model-name}") String embeddingModelName) {
        return new EmbeddingClient(apiKey, embeddingModelName, 768);
    }

    @Bean
    public TavilyClient tavilyClient() {
        return new TavilyClient(tavilyApiKey);
    }

    @Bean
    public ChatModel chatModel(
            @Value("${dashscope.api-key}") String apiKey,
            @Value("${dashscope.model-name}") String modelName) {
        return OpenAiChatModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(apiKey)
                .modelName(modelName)
                .temperature(0.2)
                .build();
    }

    @Bean
    public CourseDataTools courseDataTools(JdbcTemplate jdbc,
                                           EmbeddingClient embeddingClient) {
        return new CourseDataTools(jdbc, embeddingClient);
    }

    @Bean
    public CourseSectionTools courseSectionTools(JdbcTemplate jdbc) {
        return new CourseSectionTools(jdbc);
    }

    @Bean
    public GraduationTools graduationTools(JdbcTemplate jdbc) {
        return new GraduationTools(jdbc);
    }

    @Bean
    public ProfessorRatingTools professorRatingTools(TavilyClient tavilyClient) {
        return new ProfessorRatingTools(tavilyClient);
    }

    @Bean
    public SkillTools skillTools(JdbcTemplate jdbc) {
        return new SkillTools(jdbc);
    }

    @Bean
    public ConversationStore conversationStore(JdbcTemplate jdbc) {
        return new SupabaseConversationStore(jdbc);
    }

    @Bean
    public DistillationService distillationService(ConversationStore conversationStore,
                                                    ChatModel chatModel) {
        return new DistillationService(conversationStore, chatModel);
    }

    @Bean
    public UserProfileStore userProfileStore(JdbcTemplate jdbc) {
        return new SupabaseUserProfileStore(jdbc);
    }

    @Bean
    public ProfileExtractor profileExtractor(UserProfileStore userProfileStore,
                                              ChatModel chatModel) {
        return new ProfileExtractor(userProfileStore, chatModel);
    }

    @Bean
    public ConversationService conversationService(CompiledGraph<MainState> compiledGraph,
                                                    ConversationStore conversationStore,
                                                    DistillationService distillationService,
                                                    ProfileExtractor profileExtractor) {
        return new ConversationService(compiledGraph, conversationStore, distillationService, profileExtractor);
    }

    @Bean
    public CompiledGraph<MainState> compiledGraph(
            RouterClient routerClient,
            ChatModel chatModel,
            CourseDataTools courseDataTools,
            CourseSectionTools courseSectionTools,
            GraduationTools graduationTools,
            ProfessorRatingTools professorRatingTools,
            SkillTools skillTools) throws Exception {
        return ParentGraph.build(
                routerClient,
                chatModel,
                courseDataTools,
                courseSectionTools,
                graduationTools,
                professorRatingTools,
                skillTools);
    }
}

package com.college_advisor.service.graph.nodes.executionNodes.SimpleTaskNode;

import com.college_advisor.service.agent.ReactAgent;
import com.college_advisor.service.agent.ReactResult;
import com.college_advisor.service.graph.state.ErrorState.ErrorContext;
import com.college_advisor.service.graph.state.ErrorState.ErrorInfo;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.tools.CourseDataTools;
import com.college_advisor.service.tools.CourseSectionTools;
import com.college_advisor.service.tools.GraduationTools;
import com.college_advisor.service.tools.ProfessorRatingTools;
import dev.langchain4j.model.chat.ChatModel;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.Map;

public class SimpleTaskNode implements NodeAction<MainState> {

    private static final String SYSTEM_PROMPT = """
            You are handling a simple factual lookup task.
            The user is asking a straightforward question about courses, prerequisites, sections, or graduation requirements.
            Use the available tools to retrieve the answer directly. Do not over-explain or give unsolicited advice.
            """;

    private final ReactAgent reactAgent;

    public SimpleTaskNode(ChatModel model,
                          CourseDataTools courseData,
                          CourseSectionTools sections,
                          GraduationTools graduation,
                          ProfessorRatingTools profRating) {
        this.reactAgent = new ReactAgent(model, SYSTEM_PROMPT, courseData, sections, graduation, profRating);
    }

    public SimpleTaskNode() {
        this.reactAgent = null;
    }

    @Override
    public Map<String, Object> apply(MainState state) throws Exception {
        System.out.println("[simple_task] executing");

        if (reactAgent == null) {
            return Map.of(
                    "response",    "stub: simple_task executed",
                    "nodeHistory", "simple_task"
            );
        }

        ReactResult result = reactAgent.run(buildContextualInput(state.userInput(), state.conversationSummary()));
        if (!result.success()) {
            ErrorInfo err = new ErrorInfo("simple_task", "AGENT_ERROR", result.error(), result.retryable());
            return Map.of(
                    "errorContext", new ErrorContext(err, state.errorContext().nodeRetries(), null),
                    "nodeHistory",  "simple_task"
            );
        }
        return Map.of(
                "response",    result.content() != null ? result.content() : "",
                "nodeHistory", "simple_task"
        );
    }

    private static String buildContextualInput(String userInput, String summary) {
        if (summary == null || summary.isEmpty()) return userInput;
        return "Conversation history:\n" + summary + "\n\nCurrent question: " + userInput;
    }

    public String route(MainState state) throws Exception {
        if (state.currentError() != null) return "error_handler";
        return "output";
    }
}

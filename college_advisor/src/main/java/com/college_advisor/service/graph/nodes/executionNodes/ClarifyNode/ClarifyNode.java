package com.college_advisor.service.graph.nodes.executionNodes.ClarifyNode;

import com.college_advisor.service.graph.state.MainState;
import dev.langchain4j.model.chat.ChatModel;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.Map;

public class ClarifyNode implements NodeAction<MainState> {

    private final ChatModel model;

    public ClarifyNode(ChatModel model) {
        this.model = model;
    }

    /** 骨架 / 测试用无参构造器 */
    public ClarifyNode() {
        this(null);
    }

    @Override
    public Map<String, Object> apply(MainState state) throws Exception {
        System.out.println("[clarify] executing");

        if (model == null) {
            return Map.of("response", "stub: clarify 回复", "nodeHistory", "clarify");
        }

        String historyText = state.conversationSummary();
        String contextPrefix = historyText.isEmpty()
                ? ""
                : "Conversation history:\n" + historyText + "\n\n";

        String prompt = contextPrefix
                + "The user sent a message that is too vague to answer directly: \""
                + state.userInput() + "\"\n"
                + "Ask them exactly one short clarifying question to understand what they need.\n"
                + "Do not repeat a question already asked in the conversation history.\n"
                + "Do not answer the question. Do not explain yourself. Just ask the question.";

        String response = model.chat(prompt);

        return Map.of(
                "response",    response,
                "nodeHistory", "clarify"
        );
    }

    public String route(MainState state) throws Exception {
        if (state.currentError() != null) return "error_handler";
        return "output";
    }
}

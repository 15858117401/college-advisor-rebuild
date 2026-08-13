package com.college_advisor.service.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;

/**
 * Explicit termination signal for ReAct agents.
 * Stateful: stores the final answer so ReactAgent can retrieve it even when
 * agent.chat() returns "" (which happens when the last AI action is a tool call).
 */
public class TerminateTool {

    private volatile String capturedAnswer;

    @Tool("Call this when you have your final answer or when no tool can help. " +
          "Pass your complete final answer as the argument. " +
          "Do NOT continue calling other tools after you call this.")
    public String terminate(@P("Your complete final answer, or explanation of why you cannot answer") String answer) {
        this.capturedAnswer = answer;
        return "ok";
    }

    public String getCapturedAnswer() {
        return capturedAnswer;
    }
}

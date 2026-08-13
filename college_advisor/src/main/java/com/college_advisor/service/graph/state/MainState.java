package com.college_advisor.service.graph.state;

import com.college_advisor.service.graph.state.ErrorState.ErrorContext;
import com.college_advisor.service.graph.state.ErrorState.ErrorInfo;
import org.bsc.langgraph4j.state.AgentState;
import org.bsc.langgraph4j.state.Channel;
import org.bsc.langgraph4j.state.Channels;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MainState extends AgentState {

    public static final Map<String, Channel<?>> SCHEMA;

    static {
        SCHEMA = new HashMap<>();
        SCHEMA.put("errorContext",      Channels.base(ErrorContext::new));
        SCHEMA.put("nodeHistory",       Channels.appender(ArrayList::new));
        SCHEMA.put("taskContext",       Channels.base((java.util.function.Supplier<TaskContext>) TaskContext::new));
        SCHEMA.put("userPreferences",   Channels.base(UserPreferences::empty));
        SCHEMA.put("conversationId",      Channels.base(() -> ""));
        SCHEMA.put("userId",              Channels.base(() -> ""));
        SCHEMA.put("conversationSummary", Channels.base(() -> ""));
    }

    public MainState(Map<String, Object> initData) {
        super(initData);
    }

    @SuppressWarnings("unchecked")
    public List<String> nodeHistory() {
        return this.<List<String>>value("nodeHistory").orElseGet(ArrayList::new);
    }

    public String response() {
        return this.<String>value("response").orElse("");
    }

    public String routeDecision() {
        return this.<String>value("routeDecision").orElse("simple_task");
    }

    public String userInput() {
        return this.<String>value("userInput").orElse("");
    }

    public TaskContext taskContext() {
        return this.<TaskContext>value("taskContext").orElseGet(TaskContext::new);
    }

    /** Convenience accessor — reads through taskContext. */
    public Plan plan() {
        return taskContext().plan();
    }

    public String currentTaskId() {
        return this.<String>value("currentTaskId").orElse("");
    }

    public ErrorContext errorContext() {
        return this.<ErrorContext>value("errorContext").orElseGet(ErrorContext::new);
    }

    public ErrorInfo currentError() {
        return errorContext().currentError();
    }

    public UserPreferences userPreferences() {
        return this.<UserPreferences>value("userPreferences").orElseGet(UserPreferences::empty);
    }

    public String conversationId() {
        return this.<String>value("conversationId").orElse("");
    }

    public String userId() {
        return this.<String>value("userId").orElse("");
    }

    public String conversationSummary() {
        return this.<String>value("conversationSummary").orElse("");
    }
}

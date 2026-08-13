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

public class SubgraphState extends AgentState {

    public static final Map<String, Channel<?>> SCHEMA;

    static {
        SCHEMA = new HashMap<>();
        SCHEMA.put("plan",            Channels.base(() -> new Plan(List.of())));
        SCHEMA.put("taskResults",     Channels.appender(ArrayList::new));
        SCHEMA.put("errorContext",    Channels.base(ErrorContext::new));
        SCHEMA.put("nodeHistory",     Channels.appender(ArrayList::new));
        SCHEMA.put("userPreferences", Channels.base(UserPreferences::empty));
    }

    public SubgraphState(Map<String, Object> initData) {
        super(initData);
    }

    public Plan plan() {
        return this.<Plan>value("plan").orElseGet(() -> new Plan(List.of()));
    }

    @SuppressWarnings("unchecked")
    public List<List<TaskResult>> taskResults() {
        return this.<List<List<TaskResult>>>value("taskResults").orElseGet(List::of);
    }

    public String currentTaskId() {
        return this.<String>value("currentTaskId").orElse("");
    }

    public String userInput() {
        return this.<String>value("userInput").orElse("");
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

    @SuppressWarnings("unchecked")
    public List<String> nodeHistory() {
        return this.<List<String>>value("nodeHistory").orElseGet(ArrayList::new);
    }
}

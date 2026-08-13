package com.college_advisor.service.graph.state;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

public class TaskContext implements Serializable {

    private final Plan plan;
    private final String result;

    public TaskContext() {
        this.plan   = new Plan(List.of());
        this.result = "";
    }

    public TaskContext(Plan plan, String result) {
        this.plan   = Objects.requireNonNullElseGet(plan, () -> new Plan(List.of()));
        this.result = Objects.requireNonNullElse(result, "");
    }

    public Plan plan()     { return plan; }
    public String result() { return result; }

    public TaskContext withPlan(Plan plan)     { return new TaskContext(plan, this.result); }
    public TaskContext withResult(String result) { return new TaskContext(this.plan, result); }
}

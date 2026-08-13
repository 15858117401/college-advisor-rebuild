package com.college_advisor.service.graph.state;

import java.io.Serializable;
import java.util.List;

public record PlanTask(
        String id,
        String taskType,
        String goal,
        List<String> constraints
) implements Serializable {}

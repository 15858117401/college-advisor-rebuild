package com.college_advisor.service.graph.state;

import java.io.Serializable;

public record TaskResult(String taskId, String result) implements Serializable {}

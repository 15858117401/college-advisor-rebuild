package com.college_advisor.service.graph.state.ErrorState;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

public record ErrorContext(
        ErrorInfo currentError,            // null 表示无错误
        Map<String, Integer> nodeRetries,  // 各节点已重试次数
        String errorDecision               // error_handler 的路由决策
) implements Serializable {

    /** 供 Channels.base() 使用的无参构造器 */
    public ErrorContext() {
        this(null, new HashMap<>(), null);
    }
}

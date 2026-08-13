package com.college_advisor.service.graph.state.ErrorState;

public class ErrorInfo implements java.io.Serializable {
    public String sourceNode;
    public String type;
    public String message;
    public boolean retryable;

    public ErrorInfo(String sourceNode, String type, String message, boolean retryable) {
        this.sourceNode = sourceNode;
        this.type       = type;
        this.message    = message;
        this.retryable  = retryable;
    }
}

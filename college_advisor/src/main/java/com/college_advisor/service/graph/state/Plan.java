package com.college_advisor.service.graph.state;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.Serializable;
import java.util.List;

public record Plan(List<List<PlanTask>> chains) implements Serializable {

    /** Parses a JSON string into a Plan. Strips markdown fences if present. */
    public static Plan fromJson(String json, ObjectMapper mapper) throws Exception {
        String cleaned = stripFences(json);
        return mapper.readValue(cleaned, Plan.class);
    }

    private static String stripFences(String text) {
        if (text == null) return "{}";
        String s = text.strip();
        if (s.startsWith("```")) {
            int start = s.indexOf('\n');
            int end   = s.lastIndexOf("```");
            if (start >= 0 && end > start) return s.substring(start + 1, end).strip();
        }
        return s;
    }
}

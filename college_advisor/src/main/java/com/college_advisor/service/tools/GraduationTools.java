package com.college_advisor.service.tools;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.agent.tool.Tool;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.List;
import java.util.Map;

/**
 * Graduation requirement tools.
 * Used by: SimpleTaskNode, RecommenderNode, CoursePlannerNode (future).
 */
public class GraduationTools {

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper = new ObjectMapper();

    public GraduationTools(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Tool("Get the STAT major graduation requirements, including the required course sequence and advanced elective options. " +
         "Use when: the student asks about major requirements, required courses, or elective categories.")
    public String getGraduationRequirements() throws Exception {
        List<Map<String, Object>> rows = jdbc.query(
            "SELECT major, requirements_text FROM requirements",
            (rs, i) -> Map.of(
                "major", rs.getString("major"),
                "requirements_text", rs.getString("requirements_text")
            )
        );

        if (rows.isEmpty()) {
            return mapper.writeValueAsString(Map.of("error", "未找到毕业要求"));
        }
        return mapper.writeValueAsString(Map.of("requirements", rows));
    }
}

package com.college_advisor.service.tools;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import jakarta.annotation.Nullable;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Section scheduling tools: time slots, CRN, instructor, location.
 * Used by: SimpleTaskNode, RecommenderNode, SchedulerNode (future).
 */
public class CourseSectionTools {

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper = new ObjectMapper();

    public CourseSectionTools(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Tool("Get all sections for a course (meeting times, CRN, instructor, location, section_type). " +
         "Use when: asking about course schedules ('when does STAT 432 meet', 'who teaches STAT 107'); " +
         "or when building a schedule with time preferences. " +
         "afterHour/beforeHour are optional filters; omit to return all sections.")
    public String getCourseSections(
            @P("Course code, e.g. 'STAT 432'") String courseCode,
            @P("Only return sections starting at or after this hour (24h, e.g. 12 = noon or later) (optional)") @Nullable Integer afterHour,
            @P("Only return sections starting before this hour (24h, e.g. 17 = before 5pm) (optional)") @Nullable Integer beforeHour) throws Exception {
        List<String> conditions = new ArrayList<>();
        List<Object> params = new ArrayList<>();
        conditions.add("course_code = ?");
        params.add(courseCode);

        if (afterHour != null) {
            conditions.add("EXTRACT(HOUR FROM time_start::time) >= ?");
            params.add(afterHour);
        }
        if (beforeHour != null) {
            conditions.add("EXTRACT(HOUR FROM time_start::time) < ?");
            params.add(beforeHour);
        }

        String sql = "SELECT section_type, section, crn, days, time_start, time_end, location, instructor " +
                     "FROM course_sections WHERE " + String.join(" AND ", conditions) +
                     " ORDER BY section_type, section";

        List<Map<String, Object>> rows = jdbc.query(
            sql,
            (rs, i) -> {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("section_type", rs.getString("section_type"));
                row.put("section", rs.getString("section"));
                row.put("crn", rs.getString("crn"));
                row.put("days", rs.getString("days"));
                row.put("time_start", rs.getString("time_start"));
                row.put("time_end", rs.getString("time_end"));
                row.put("location", rs.getString("location"));
                row.put("instructor", rs.getString("instructor"));
                return row;
            },
            params.toArray()
        );

        if (rows.isEmpty()) {
            return mapper.writeValueAsString(Map.of(
                "course_code", courseCode,
                "sections", List.of(),
                "note", "没有符合时间条件的 section"
            ));
        }
        return mapper.writeValueAsString(Map.of("course_code", courseCode, "sections", rows));
    }
}

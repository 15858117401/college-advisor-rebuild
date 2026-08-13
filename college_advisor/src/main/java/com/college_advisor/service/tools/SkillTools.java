package com.college_advisor.service.tools;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.ResultSetMetaData;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Skill document loader — RecommenderNode exclusive.
 * Loads strategy markdown from resources/skills/ and appends pre-fetched DB data.
 */
public class SkillTools {

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper = new ObjectMapper();

    public SkillTools(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Tool("Load a recommender strategy document with pre-fetched course data. " +
         "WHEN TO CALL: Only in the very first tool call of your reasoning, before any other tool. " +
         "NEVER call this after you have already called any tool. " +
         "Skill names and their triggers: " +
         "- 'minimal_graduation': easy graduation, light workload, low effort, no attendance, online, afternoon sections, minimal, stress-free " +
         "- 'grad_school_prep': grad school, PhD, master's, research, doctoral, academic rigor, graduate application " +
         "CONSTRAINT: Call this at most once per task. After loading, use the pre-fetched data in the document directly — do not re-run those queries.")
    public String loadSkill(
            @P("skill 名称：'minimal_graduation' 或 'grad_school_prep'") String skillName) throws Exception {
        String staticContent = loadMarkdown(skillName);
        String prefetched = prefetch(skillName);
        return staticContent + "\n\n" + prefetched;
    }

    private String loadMarkdown(String skillName) throws Exception {
        String path = "skills/" + skillName + ".md";
        try (InputStream in = SkillTools.class.getClassLoader().getResourceAsStream(path)) {
            if (in == null) {
                return "# Skill not found: " + skillName +
                       "\nAvailable: minimal_graduation, grad_school_prep";
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private LinkedHashMap<String, Object> mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
        LinkedHashMap<String, Object> row = new LinkedHashMap<>();
        ResultSetMetaData meta = rs.getMetaData();
        for (int i = 1; i <= meta.getColumnCount(); i++) {
            row.put(meta.getColumnName(i), rs.getObject(i));
        }
        return row;
    }

    private String prefetch(String skillName) throws Exception {
        return switch (skillName) {
            case "grad_school_prep"   -> prefetchGradSchool();
            case "minimal_graduation" -> prefetchMinimalGraduation();
            default -> "## Pre-fetched Data\n(none for this skill)";
        };
    }

    private String prefetchGradSchool() throws Exception {
        List<Map<String, Object>> requiredCore = jdbc.query(
            "SELECT course_code, difficulty, avg_gpa, workload_hrs_per_week " +
            "FROM course_chunks WHERE role = 'required' " +
            "AND course_code NOT IN ('STAT 107', 'STAT 200', 'STAT 212') " +
            "ORDER BY course_code",
            (rs, i) -> mapRow(rs)
        );
        List<Map<String, Object>> theoryElectives = jdbc.query(
            "SELECT course_code, difficulty, avg_gpa, workload_hrs_per_week " +
            "FROM course_chunks WHERE role = 'elective' AND difficulty IN ('Medium','Hard') " +
            "ORDER BY avg_gpa DESC",
            (rs, i) -> mapRow(rs)
        );
        return "## Pre-fetched Data (do NOT re-run these searches)\n\n" +
               "### Required core (theory foundation)\n" +
               mapper.writeValueAsString(requiredCore) + "\n\n" +
               "### Theory-heavy electives (recommended for grad school)\n" +
               mapper.writeValueAsString(theoryElectives);
    }

    private String prefetchMinimalGraduation() throws Exception {
        List<Map<String, Object>> introCourses = jdbc.query(
            "SELECT course_code, difficulty, avg_gpa, workload_hrs_per_week, attendance_required " +
            "FROM course_chunks WHERE course_code IN ('STAT 107', 'STAT 200', 'STAT 212') " +
            "ORDER BY workload_hrs_per_week ASC",
            (rs, i) -> mapRow(rs)
        );
        List<Map<String, Object>> requiredCore = jdbc.query(
            "SELECT course_code, difficulty, avg_gpa, workload_hrs_per_week " +
            "FROM course_chunks WHERE role = 'required' " +
            "AND course_code NOT IN ('STAT 107', 'STAT 200', 'STAT 212') " +
            "ORDER BY course_code",
            (rs, i) -> mapRow(rs)
        );
        List<Map<String, Object>> electivePool = jdbc.query(
            "SELECT course_code, difficulty, avg_gpa, workload_hrs_per_week, attendance_required " +
            "FROM course_chunks WHERE role = 'elective' " +
            "ORDER BY workload_hrs_per_week ASC, avg_gpa DESC",
            (rs, i) -> mapRow(rs)
        );
        return "## Pre-fetched Data (do NOT re-run these searches)\n\n" +
               "### Intro course options (pick 1)\n" +
               mapper.writeValueAsString(introCourses) + "\n\n" +
               "### Required core (unavoidable)\n" +
               mapper.writeValueAsString(requiredCore) + "\n\n" +
               "### Elective pool — choose 4, sorted by workload ASC\n" +
               mapper.writeValueAsString(electivePool);
    }
}

package com.college_advisor.service.tools;

import com.college_advisor.service.rag.client.EmbeddingClient;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import jakarta.annotation.Nullable;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.StringJoiner;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Core course lookup tools used by most agents.
 * Covers: semantic search, detail lookup, attribute filtering, and eligibility check.
 */
public class CourseDataTools {

    private static final Pattern COURSE_CODE_PATTERN = Pattern.compile("[A-Z]{2,4}\\s+\\d{3}");

    private final JdbcTemplate jdbc;
    private final EmbeddingClient embeddingClient;
    private final ObjectMapper mapper = new ObjectMapper();

    public CourseDataTools(JdbcTemplate jdbc, EmbeddingClient embeddingClient) {
        this.jdbc = jdbc;
        this.embeddingClient = embeddingClient;
    }

    @Tool("Semantic search for courses by topic or description. " +
         "Use when: the student asks about courses in a subject area (e.g. 'any machine learning courses', 'find stats programming courses'). " +
         "Returns the most relevant courses with basic info. limit defaults to 5, max 10.")
    public String searchCourses(
            @P("Search query or description, e.g. 'machine learning' or 'data analysis programming'") String query,
            @P("Number of results, default 5, max 10 (optional)") @Nullable Integer limit) throws Exception {
        int lim = (limit == null) ? 5 : Math.min(limit, 10);

        float[] embedding = embeddingClient.embedText(query);
        StringJoiner sj = new StringJoiner(",", "[", "]");
        for (float v : embedding) sj.add(Float.toString(v));
        String vecStr = sj.toString();

        List<Map<String, Object>> rows = jdbc.query(
            "SELECT course_code, role, difficulty, avg_gpa, chunk_text " +
            "FROM course_chunks ORDER BY embedding <=> ?::vector LIMIT ?",
            (rs, i) -> {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("course_code", rs.getString("course_code"));
                row.put("role", rs.getString("role"));
                row.put("difficulty", rs.getString("difficulty"));
                row.put("avg_gpa", rs.getBigDecimal("avg_gpa"));
                row.put("chunk_text", rs.getString("chunk_text"));
                return row;
            },
            vecStr, lim
        );

        return mapper.writeValueAsString(Map.of("courses", rows));
    }

    @Tool("Look up full details for a specific course by code. " +
         "Use when: the student asks about a specific course (e.g. 'what is STAT 432', 'is STAT 107 hard', 'how many credits is STAT 400', 'what are the prerequisites').")
    public String getCourseDetails(
            @P("Course code, e.g. 'STAT 432'") String courseCode) throws Exception {
        List<Map<String, Object>> rows = jdbc.query(
            "SELECT course_code, role, avg_gpa, difficulty, workload_hrs_per_week, attendance_required, chunk_text " +
            "FROM course_chunks WHERE course_code = ?",
            (rs, i) -> {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("course_code", rs.getString("course_code"));
                row.put("role", rs.getString("role"));
                row.put("avg_gpa", rs.getBigDecimal("avg_gpa"));
                row.put("difficulty", rs.getString("difficulty"));
                row.put("workload_hrs_per_week", rs.getInt("workload_hrs_per_week"));
                row.put("attendance_required", rs.getObject("attendance_required"));
                row.put("chunk_text", rs.getString("chunk_text"));
                return row;
            },
            courseCode
        );

        if (rows.isEmpty()) {
            return mapper.writeValueAsString(Map.of("error", "未找到课程: " + courseCode));
        }
        return mapper.writeValueAsString(rows.get(0));
    }

    @Tool("Filter courses by structured criteria. Use when the student describes course characteristics rather than a specific name. " +
         "'easy course' → difficulty=Low and/or minAvgGpa=3.2; " +
         "'light workload' → maxWorkloadHrs=6; " +
         "'no attendance' → attendanceRequired=false; " +
         "'required courses' → role=required. Combine multiple criteria as needed.")
    public String filterCourses(
            @P("Difficulty: Low / Medium / Hard (optional)") @Nullable String difficulty,
            @P("Max workload hours per week (optional)") @Nullable Integer maxWorkloadHrs,
            @P("Minimum average GPA (optional)") @Nullable Double minAvgGpa,
            @P("Whether attendance is required (optional)") @Nullable Boolean attendanceRequired,
            @P("Course role: 'required' for required courses, omit for all (optional)") @Nullable String role) throws Exception {
        List<String> conditions = new ArrayList<>();
        List<Object> params = new ArrayList<>();

        if (difficulty != null) {
            conditions.add("difficulty = ?");
            params.add(difficulty);
        }
        if (maxWorkloadHrs != null) {
            conditions.add("workload_hrs_per_week <= ?");
            params.add(maxWorkloadHrs);
        }
        if (minAvgGpa != null) {
            conditions.add("avg_gpa >= ?");
            params.add(minAvgGpa);
        }
        if (attendanceRequired != null) {
            conditions.add("attendance_required = ?");
            params.add(attendanceRequired);
        }
        if (role != null) {
            conditions.add("role = ?");
            params.add(role);
        }

        String where = conditions.isEmpty() ? "" : " WHERE " + String.join(" AND ", conditions);
        String sql = "SELECT course_code, role, difficulty, avg_gpa, " +
                     "workload_hrs_per_week, attendance_required FROM course_chunks" + where +
                     " ORDER BY avg_gpa DESC NULLS LAST LIMIT 20";

        List<Map<String, Object>> rows = jdbc.query(
            sql,
            (rs, i) -> {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("course_code", rs.getString("course_code"));
                row.put("role", rs.getString("role"));
                row.put("difficulty", rs.getString("difficulty"));
                row.put("avg_gpa", rs.getBigDecimal("avg_gpa"));
                row.put("workload_hrs_per_week", rs.getString("workload_hrs_per_week"));
                row.put("attendance_required", rs.getObject("attendance_required"));
                return row;
            },
            params.toArray()
        );

        return mapper.writeValueAsString(Map.of("courses", rows, "count", rows.size()));
    }

    @Tool("Given a list of completed courses, return all courses whose prerequisites are fully satisfied (i.e. the student is eligible to enroll). " +
         "Use for: 'I've taken STAT 107 and STAT 200, what can I take now?', or to determine the available course pool for recommendations. " +
         "Already-completed courses are excluded from the result.")
    public String findAvailableCourses(
            @P("List of completed course codes, e.g. [\"STAT 107\", \"STAT 200\"]") List<String> completedCourses) throws Exception {
        Set<String> completedSet = completedCourses.stream()
                .map(String::trim)
                .map(String::toUpperCase)
                .collect(Collectors.toSet());

        List<Map<String, Object>> allCourses = jdbc.query(
            "SELECT course_code, role, difficulty, avg_gpa, workload_hrs_per_week, " +
            "       attendance_required, chunk_text " +
            "FROM course_chunks ORDER BY course_code",
            (rs, i) -> {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("course_code", rs.getString("course_code"));
                row.put("role", rs.getString("role"));
                row.put("difficulty", rs.getString("difficulty"));
                row.put("avg_gpa", rs.getBigDecimal("avg_gpa"));
                row.put("workload_hrs_per_week", rs.getObject("workload_hrs_per_week"));
                row.put("attendance_required", rs.getObject("attendance_required"));
                row.put("chunk_text", rs.getString("chunk_text"));
                return row;
            }
        );

        List<Map<String, Object>> available = allCourses.stream()
                .filter(c -> !completedSet.contains(normalize(c.get("course_code"))))
                .filter(c -> {
                    List<String> prereqs = extractPrerequisites((String) c.get("chunk_text"));
                    return completedSet.containsAll(prereqs);
                })
                .map(c -> {
                    Map<String, Object> out = new LinkedHashMap<>(c);
                    out.remove("chunk_text");
                    return out;
                })
                .toList();

        return mapper.writeValueAsString(Map.of(
            "completed_courses", completedCourses,
            "available_courses", available,
            "count", available.size()
        ));
    }

    @Tool("Find all courses that list a given course as a prerequisite (reverse prerequisite lookup). " +
         "Use when: the student asks what they can take after completing a course (e.g. 'I finished STAT 107, what can I take next?').")
    public String findCoursesByPrerequisite(
            @P("Completed course code, e.g. 'STAT 107'") String completedCourseCode) throws Exception {
        List<Map<String, Object>> rows = jdbc.query(
            "SELECT course_code, difficulty, avg_gpa, chunk_text " +
            "FROM course_chunks WHERE chunk_text ILIKE '%Prerequisites:%' || ? || '%' ORDER BY course_code",
            (rs, i) -> {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("course_code", rs.getString("course_code"));
                row.put("difficulty", rs.getString("difficulty"));
                row.put("avg_gpa", rs.getBigDecimal("avg_gpa"));
                row.put("chunk_text", rs.getString("chunk_text"));
                return row;
            },
            completedCourseCode
        );

        return mapper.writeValueAsString(Map.of(
            "completed_course", completedCourseCode,
            "unlocked_courses", rows,
            "count", rows.size()
        ));
    }

    @Tool("Get the full prerequisite chain for a course — all ancestors resolved recursively. " +
         "Returns an ordered list from the target course back to root prerequisites. " +
         "Use when planning semesters ahead: tells you the minimum course sequence and ordering constraints.")
    public String getPrerequisiteChain(
            @P("Course code, e.g. 'STAT 432'") String courseCode) throws Exception {
        List<Map<String, Object>> chain = new ArrayList<>();
        resolveChain(courseCode.trim().toUpperCase(), new java.util.LinkedHashSet<>(), chain);
        return mapper.writeValueAsString(Map.of(
            "course", courseCode,
            "prerequisite_chain", chain
        ));
    }

    private void resolveChain(String code, java.util.LinkedHashSet<String> visited,
                               List<Map<String, Object>> chain) {
        if (!visited.add(code)) return;
        List<Map<String, Object>> rows = jdbc.query(
            "SELECT course_code, chunk_text FROM course_chunks WHERE course_code = ? LIMIT 1",
            (rs, i) -> Map.of(
                "course_code", rs.getString("course_code"),
                "chunk_text",  rs.getString("chunk_text")),
            code);
        if (rows.isEmpty()) return;
        List<String> prereqs = extractPrerequisites((String) rows.get(0).get("chunk_text"));
        chain.add(Map.of("course_code", code, "prerequisites", prereqs));
        for (String prereq : prereqs) resolveChain(prereq, visited, chain);
    }

    @Tool("Find courses taught by a given instructor. Use when: the student asks what a professor teaches " +
         "(e.g. 'what does Professor Wang teach?'). Returns course codes and instructor full name.")
    public String findCoursesByInstructor(
            @P("Instructor name or last name, e.g. 'Wang' or 'Professor Smith'") String instructorName) throws Exception {
        List<Map<String, Object>> rows = jdbc.query(
            "SELECT DISTINCT course_code, instructor FROM course_sections " +
            "WHERE instructor ILIKE ? ORDER BY course_code",
            (rs, i) -> {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("course_code", rs.getString("course_code"));
                row.put("instructor",  rs.getString("instructor"));
                return row;
            },
            "%" + instructorName + "%"
        );

        return mapper.writeValueAsString(Map.of(
            "instructor_query", instructorName,
            "courses", rows,
            "count", rows.size()
        ));
    }

    private List<String> extractPrerequisites(String chunkText) {
        if (chunkText == null) return List.of();
        int idx = chunkText.indexOf("Prerequisites:");
        if (idx == -1) return List.of();

        String section = chunkText.substring(idx + "Prerequisites:".length());
        int nextNewline = section.indexOf('\n');
        if (nextNewline != -1) section = section.substring(0, nextNewline);

        if (section.isBlank() || section.toLowerCase().contains("none")) return List.of();

        Matcher m = COURSE_CODE_PATTERN.matcher(section);
        List<String> prereqs = new ArrayList<>();
        while (m.find()) prereqs.add(m.group().toUpperCase());
        return prereqs;
    }

    private String normalize(Object code) {
        return code == null ? "" : code.toString().trim().toUpperCase();
    }
}

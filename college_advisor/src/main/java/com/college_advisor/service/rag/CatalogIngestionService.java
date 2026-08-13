package com.college_advisor.service.rag;

import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.rag.dto.CourseDraft;
import com.college_advisor.service.rag.dto.CourseSectionDraft;
import com.college_advisor.service.rag.dto.ParsedCatalog;
import com.pgvector.PGvector;
import org.springframework.core.io.Resource;
import org.springframework.jdbc.core.BatchPreparedStatementSetter;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.util.StreamUtils;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.sql.Array;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Types;
import java.util.List;

/**
 * Loads {@code stat.md} into {@code graduation_requirements}, {@code courses}, and {@code course_sections},
 * then writes per-course {@code embedding} from Gemini (description-first text).
 * Registered only by the standalone ingest app ({@code com.collegeadvisor.catalog}), not as a component
 * on the main {@code com.college_advisor} application.
 */
public class CatalogIngestionService {

    private static final int MAX_EMBED_CHARS = 28_000;

    private final JdbcTemplate jdbcTemplate;
    private final EmbeddingClient embeddingClient;

    private final String majorCode;

    public CatalogIngestionService(
            JdbcTemplate jdbcTemplate,
            EmbeddingClient embeddingClient,
            String majorCode) {
        this.jdbcTemplate = jdbcTemplate;
        this.embeddingClient = embeddingClient;
        this.majorCode = majorCode;
    }

    /**
     * Reads markdown from the given resource (typically {@code classpath:stat.md}).
     */
    public void ingestFromResource(Resource statMd) throws IOException {
        String markdown = StreamUtils.copyToString(statMd.getInputStream(), StandardCharsets.UTF_8);
        ingest(markdown);
    }

    public void ingest(String markdown) {
        ParsedCatalog parsed = StatMdParser.parse(markdown);
        upsertGraduationRequirements(parsed.graduationPreamble());
        for (CourseDraft course : parsed.courses()) {
            float[] embedding = embeddingClient.embedText(embeddingInput(course));
            upsertCourse(course, embedding);
            replaceSections(course.courseCode(), course.sections());
        }
    }

    private String embeddingInput(CourseDraft c) {
        String prefix = c.courseCode() + " — " + c.name();
        String body = c.description() == null ? "" : c.description();
        String tagsLine = "";
        if (c.tags() != null && !c.tags().isEmpty()) {
            tagsLine = "\n\nTags: " + String.join(", ", c.tags());
        }
        String combined = prefix + "\n\n" + body + tagsLine;
        if (combined.length() > MAX_EMBED_CHARS) {
            combined = combined.substring(0, MAX_EMBED_CHARS);
        }
        return combined;
    }

    private void upsertGraduationRequirements(String text) {
        if (text == null || text.isBlank()) {
            return;
        }
        jdbcTemplate.update(
                """
                INSERT INTO graduation_requirements (major_code, requirements_text)
                VALUES (?, ?)
                ON CONFLICT (major_code) DO UPDATE SET
                  requirements_text = EXCLUDED.requirements_text
                """,
                majorCode,
                text);
    }

    private void upsertCourse(CourseDraft c, float[] embedding) {
        PGvector vec = new PGvector(embedding);
        jdbcTemplate.update(con -> {
            PreparedStatement ps = con.prepareStatement(
                    """
                    INSERT INTO courses (
                      course_code, major, name, role, credits, prerequisites, description,
                      tags, avg_gpa, difficulty, workload_hrs_per_week, assessment_style,
                      attendance_required, embedding
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT (course_code) DO UPDATE SET
                      major = EXCLUDED.major,
                      name = EXCLUDED.name,
                      role = EXCLUDED.role,
                      credits = EXCLUDED.credits,
                      prerequisites = EXCLUDED.prerequisites,
                      description = EXCLUDED.description,
                      tags = EXCLUDED.tags,
                      avg_gpa = EXCLUDED.avg_gpa,
                      difficulty = EXCLUDED.difficulty,
                      workload_hrs_per_week = EXCLUDED.workload_hrs_per_week,
                      assessment_style = EXCLUDED.assessment_style,
                      attendance_required = EXCLUDED.attendance_required,
                      embedding = EXCLUDED.embedding
                    """);
            int i = 1;
            ps.setString(i++, c.courseCode());
            ps.setString(i++, majorCode);
            ps.setString(i++, c.name());
            ps.setString(i++, c.role());
            ps.setString(i++, c.credits());
            ps.setString(i++, c.prerequisites());
            ps.setString(i++, c.description());
            setTextArray(ps, i++, c.tags(), con);
            if (c.avgGpa() != null) {
                ps.setBigDecimal(i++, c.avgGpa());
            } else {
                ps.setNull(i++, Types.NUMERIC);
            }
            ps.setString(i++, c.difficulty());
            ps.setString(i++, c.workloadHrsPerWeek());
            ps.setString(i++, c.assessmentStyle());
            if (c.attendanceRequired() != null) {
                ps.setBoolean(i++, c.attendanceRequired());
            } else {
                ps.setNull(i++, Types.BOOLEAN);
            }
            ps.setObject(i, vec);
            return ps;
        });
    }

    private static void setTextArray(PreparedStatement ps, int index, List<String> tags, Connection conn)
            throws SQLException {
        String[] arrVals = (tags == null || tags.isEmpty()) ? new String[0] : tags.toArray(String[]::new);
        Array arr = conn.createArrayOf("text", arrVals);
        ps.setArray(index, arr);
    }

    private void replaceSections(String courseCode, List<CourseSectionDraft> sections) {
        jdbcTemplate.update("DELETE FROM course_sections WHERE course_code = ?", courseCode);
        if (sections == null || sections.isEmpty()) {
            return;
        }
        String sql =
                """
                INSERT INTO course_sections (
                  course_code, section_type, section, crn, days,
                  time_start, time_end, location, instructor
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """;
        jdbcTemplate.batchUpdate(
                sql,
                new BatchPreparedStatementSetter() {
                    @Override
                    public void setValues(PreparedStatement ps, int j) throws SQLException {
                        CourseSectionDraft row = sections.get(j);
                        int i = 1;
                        ps.setString(i++, courseCode);
                        ps.setString(i++, row.sectionType());
                        ps.setString(i++, row.section());
                        ps.setString(i++, row.crn());
                        ps.setString(i++, row.days());
                        if (row.timeStart() != null) {
                            ps.setObject(i++, row.timeStart());
                        } else {
                            ps.setNull(i++, Types.TIME);
                        }
                        if (row.timeEnd() != null) {
                            ps.setObject(i++, row.timeEnd());
                        } else {
                            ps.setNull(i++, Types.TIME);
                        }
                        ps.setString(i++, row.location());
                        ps.setString(i++, row.instructor());
                    }

                    @Override
                    public int getBatchSize() {
                        return sections.size();
                    }
                });
    }
}

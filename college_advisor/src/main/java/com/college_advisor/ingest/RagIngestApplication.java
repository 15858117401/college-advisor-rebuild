package com.college_advisor.ingest;

import com.college_advisor.service.rag.StatMdParser;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.college_advisor.service.rag.dto.CourseDraft;
import com.college_advisor.service.rag.dto.ParsedCatalog;
import com.pgvector.PGvector;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.sql.Types;
import java.util.Properties;

/**
 * Standalone RAG ingest: reads stat.md, builds one chunk per course,
 * embeds via Gemini, and upserts into course_chunks with metadata columns.
 *
 * Run with: ./mvnw spring-boot:run -Dspring-boot.run.profiles=ingest
 * (or as a plain main — no Spring context needed)
 */
public class RagIngestApplication {

    private static final int MAX_EMBED_CHARS = 28_000;

    public static void main(String[] args) throws Exception {
        Properties props = new Properties();
        try (InputStream in = RagIngestApplication.class.getResourceAsStream("/application-ingest.properties")) {
            props.load(in);
        }

        HikariConfig hikari = new HikariConfig();
        hikari.setJdbcUrl(props.getProperty("spring.datasource.url"));
        hikari.setUsername(props.getProperty("spring.datasource.username").strip());
        hikari.setPassword(props.getProperty("spring.datasource.password").strip());

        try (HikariDataSource ds = new HikariDataSource(hikari)) {
            JdbcTemplate jdbc = new JdbcTemplate(ds);

            EmbeddingClient embeddingClient = new EmbeddingClient(
                    props.getProperty("dashscope.api-key"),
                    props.getProperty("dashscope.embedding-model-name"),
                    Integer.parseInt(props.getProperty("ingest.output-dimensionality", "768"))
            );

            String major = props.getProperty("ingest.major-code", "STAT");

            String markdown;
            try (InputStream md = RagIngestApplication.class.getResourceAsStream("/stat.md")) {
                markdown = new String(md.readAllBytes(), StandardCharsets.UTF_8);
            }

            ParsedCatalog catalog = StatMdParser.parse(markdown);
            int count = 0;
            for (CourseDraft course : catalog.courses()) {
                String chunkText = buildChunkText(course);
                float[] embedding = embeddingClient.embedText(chunkText);
                upsert(jdbc, course, major, chunkText, embedding);
                System.out.printf("  [%d] %s — %s%n", ++count, course.courseCode(), course.name());
            }
            System.out.printf("RAG ingest complete: %d courses.%n", count);
        }
    }

    // ── chunk text ────────────────────────────────────────────────────────────

    private static String buildChunkText(CourseDraft c) {
        StringBuilder sb = new StringBuilder();

        // title
        sb.append(c.courseCode()).append(" — ").append(c.name()).append("\n");

        // structured metadata line (also useful for semantic search)
        sb.append("Role: ").append(nvl(c.role(), "—"));
        sb.append(" | Credits: ").append(nvl(c.credits(), "—"));
        sb.append(" | Prerequisites: ").append(nvl(c.prerequisites(), "none"));
        sb.append("\n");

        sb.append("Difficulty: ").append(nvl(c.difficulty(), "—"));
        sb.append(" | Workload: ").append(nvl(c.workloadHrsPerWeek(), "—")).append(" hrs/week");
        sb.append(" | Avg GPA: ").append(c.avgGpa() != null ? c.avgGpa().toPlainString() : "—");
        sb.append(" | Attendance required: ").append(c.attendanceRequired() != null ? (c.attendanceRequired() ? "yes" : "no") : "—");
        sb.append("\n");

        if (c.assessmentStyle() != null) {
            sb.append("Assessment: ").append(c.assessmentStyle()).append("\n");
        }

        // description
        if (c.description() != null && !c.description().isBlank()) {
            sb.append("\n").append(c.description());
        }

        String result = sb.toString();
        return result.length() > MAX_EMBED_CHARS ? result.substring(0, MAX_EMBED_CHARS) : result;
    }

    // ── upsert ────────────────────────────────────────────────────────────────

    private static void upsert(JdbcTemplate jdbc, CourseDraft c, String major,
                                String chunkText, float[] embedding) {
        PGvector vec = new PGvector(embedding);
        jdbc.update(con -> {
            var ps = con.prepareStatement("""
                    INSERT INTO course_chunks
                      (course_code, major, chunk_text, embedding,
                       role, difficulty, avg_gpa, workload_hrs_per_week, attendance_required)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT (course_code) DO UPDATE SET
                      major                 = EXCLUDED.major,
                      chunk_text            = EXCLUDED.chunk_text,
                      embedding             = EXCLUDED.embedding,
                      role                  = EXCLUDED.role,
                      difficulty            = EXCLUDED.difficulty,
                      avg_gpa               = EXCLUDED.avg_gpa,
                      workload_hrs_per_week = EXCLUDED.workload_hrs_per_week,
                      attendance_required   = EXCLUDED.attendance_required
                    """);
            int i = 1;
            ps.setString(i++, c.courseCode());
            ps.setString(i++, major);
            ps.setString(i++, chunkText);
            ps.setObject(i++, vec);
            ps.setString(i++, c.role());
            ps.setString(i++, c.difficulty());
            if (c.avgGpa() != null) {
                ps.setBigDecimal(i++, c.avgGpa());
            } else {
                ps.setNull(i++, Types.NUMERIC);
            }
            if (c.workloadHrsPerWeek() != null) {
                ps.setInt(i++, parseWorkload(c.workloadHrsPerWeek()));
            } else {
                ps.setNull(i++, Types.INTEGER);
            }
            if (c.attendanceRequired() != null) {
                ps.setBoolean(i++, c.attendanceRequired());
            } else {
                ps.setNull(i++, Types.BOOLEAN);
            }
            return ps;
        });
    }

    // ── helpers ───────────────────────────────────────────────────────────────

    private static String nvl(String s, String fallback) {
        return (s == null || s.isBlank()) ? fallback : s;
    }

    /** Parses "10" or "10 hrs/week" → 10; returns 0 on failure. */
    private static int parseWorkload(String s) {
        try {
            return Integer.parseInt(s.trim().split("[^0-9]")[0]);
        } catch (Exception e) {
            return 0;
        }
    }
}

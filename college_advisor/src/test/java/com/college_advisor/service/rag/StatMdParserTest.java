package com.college_advisor.service.rag;

import com.college_advisor.service.rag.dto.CourseDraft;
import com.college_advisor.service.rag.dto.ParsedCatalog;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

class StatMdParserTest {

    @Test
    void parse_snippet_preamble_and_one_course() {
        String md =
                """
                # Title
                ## 项目毕业要求
                - rule: one

                ---
                # STAT 400 — Statistics and Probability I
                - role: Core Required
                - term: Spring 2026
                - credits: 4 hours.
                - prerequisites: —
                - same_as: Same as MATH 463.
                - description: Intro stats.
                - schedule_url: https://example.com/400

                ## Sections
                | Type | Section | CRN | Days | Time | Location | Instructor |
                |------|---------|-----|------|------|----------|------------|
                | Lecture | LL1 | 36133 | TR | 11:00AM–12:20PM | 1320 DCL | Lee, H |

                ## Student Info [AI-estimated]
                - avg_gpa: 3.3
                - difficulty: Medium
                - workload_hrs_per_week: 8–10
                - assessment_style: Midterm + Final
                - attendance_required: No

                ## Tags
                probability, inference
                """;

        ParsedCatalog p = StatMdParser.parse(md);
        assertTrue(p.graduationPreamble().contains("项目毕业要求"));
        assertTrue(p.graduationPreamble().contains("rule: one"));
        assertEquals(1, p.courses().size());
        CourseDraft c = p.courses().get(0);
        assertEquals("STAT 400", c.courseCode());
        assertEquals("Statistics and Probability I", c.name());
        assertEquals("Core Required", c.role());
        assertNotNull(c.description());
        assertTrue(c.description().contains("Intro stats."));
        assertTrue(c.description().contains("same_as:"));
        assertTrue(c.description().contains("schedule_url:"));
        assertEquals(1, c.sections().size());
        assertEquals("36133", c.sections().get(0).crn());
        assertNotNull(c.sections().get(0).timeStart());
        assertNotNull(c.sections().get(0).timeEnd());
        assertEquals(2, c.tags().size());
        assertEquals("Medium", c.difficulty());
        assertNotNull(c.avgGpa());
        assertEquals(Boolean.FALSE, c.attendanceRequired());
    }

    @Test
    void parse_full_stat_md_from_classpath() throws Exception {
        try (var in = getClass().getResourceAsStream("/stat.md")) {
            assertNotNull(in);
            String md = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            ParsedCatalog p = StatMdParser.parse(md);
            assertFalse(p.graduationPreamble().isBlank());
            assertTrue(p.courses().size() >= 10, "expected many courses, got " + p.courses().size());
            long withSections =
                    p.courses().stream().filter(c -> !c.sections().isEmpty()).count();
            assertTrue(withSections >= 5, "expected several courses with sections");
        }
    }
}

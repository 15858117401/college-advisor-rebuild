package com.college_advisor.service.rag.dto;

import java.math.BigDecimal;
import java.util.List;

/**
 * One row for {@code courses} plus child sections, before persistence.
 */
public record CourseDraft(
        String courseCode,
        String name,
        String role,
        String credits,
        String prerequisites,
        String description,
        List<String> tags,
        BigDecimal avgGpa,
        String difficulty,
        String workloadHrsPerWeek,
        String assessmentStyle,
        Boolean attendanceRequired,
        List<CourseSectionDraft> sections
) {}

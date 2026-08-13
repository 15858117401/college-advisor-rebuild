package com.college_advisor.service.rag.dto;

import java.time.LocalTime;

/**
 * One row for {@code course_sections} before persistence.
 */
public record CourseSectionDraft(
        String sectionType,
        String section,
        String crn,
        String days,
        String timeRaw,
        LocalTime timeStart,
        LocalTime timeEnd,
        String location,
        String instructor
) {}

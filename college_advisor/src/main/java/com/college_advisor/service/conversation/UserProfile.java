package com.college_advisor.service.conversation;

import java.util.List;
import java.util.Map;

/** Extracted user profile from a conversation summary. schedule is the flat new schedule. */
public record UserProfile(
        String year,
        List<String> completedCourses,
        Map<String, Object> preferences,
        Map<String, Object> schedule
) {
    boolean isEmpty() {
        return year == null && completedCourses == null && preferences == null && schedule == null;
    }
}

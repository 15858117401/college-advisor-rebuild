package com.college_advisor.service.conversation;

import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class ProfileMergeTest {

    @Test
    void yearOverwritesWhenExtracted() {
        assertEquals("junior",   SupabaseUserProfileStore.mergedYear("freshman", "junior"));
        assertEquals("freshman", SupabaseUserProfileStore.mergedYear("freshman", null));
        assertEquals("junior",   SupabaseUserProfileStore.mergedYear(null, "junior"));
        assertNull(              SupabaseUserProfileStore.mergedYear(null, null));
    }

    @Test
    void coursesUnionAndDeduplicate() {
        List<String> existing  = List.of("STAT 400", "MATH 241");
        List<String> extracted = List.of("STAT 400", "STAT 432");
        List<String> merged    = SupabaseUserProfileStore.mergedCourses(existing, extracted);
        assertEquals(3, merged.size());
        assertTrue(merged.containsAll(List.of("STAT 400", "MATH 241", "STAT 432")));
    }

    @Test
    void coursesNullExtractedKeepsExisting() {
        List<String> existing = List.of("STAT 400");
        assertEquals(existing, SupabaseUserProfileStore.mergedCourses(existing, null));
    }

    @Test
    void coursesNullBothReturnsNull() {
        assertNull(SupabaseUserProfileStore.mergedCourses(null, null));
    }

    @Test
    void prefsNullValuesDoNotEraseExisting() {
        Map<String, Object> existing = new HashMap<>(Map.of("minGpa", 3.5, "goals", "grad school"));
        Map<String, Object> extracted = new HashMap<>();
        extracted.put("minGpa", null);
        extracted.put("workload", "light");
        Map<String, Object> merged = SupabaseUserProfileStore.mergedPrefs(existing, extracted);
        assertEquals(3.5,           merged.get("minGpa"));
        assertEquals("light",       merged.get("workload"));
        assertEquals("grad school", merged.get("goals"));
    }

    @Test
    void prefsNullExtractedKeepsExisting() {
        Map<String, Object> existing = Map.of("minGpa", 3.5);
        assertEquals(existing, SupabaseUserProfileStore.mergedPrefs(existing, null));
    }

    @Test
    void schedulesRotatesCorrectly() {
        Map<String, Object> s1 = Map.of("STAT 400", "12345");
        Map<String, Object> s2 = Map.of("MATH 241", "67890");
        Map<String, Object> existing = new LinkedHashMap<>();
        existing.put("schedule1", s1);
        existing.put("schedule2", s2);

        Map<String, Object> newSchedule = Map.of("STAT 432", "11111");
        Map<String, Object> result = SupabaseUserProfileStore.mergedSchedules(existing, newSchedule);

        assertEquals(newSchedule, result.get("schedule1"));
        assertEquals(s1,          result.get("schedule2"));
        assertEquals(s2,          result.get("schedule3"));
        assertFalse(result.containsKey("schedule4"));
    }

    @Test
    void schedulesDropsOldestWhenFull() {
        Map<String, Object> s1 = Map.of("A", "1");
        Map<String, Object> s2 = Map.of("B", "2");
        Map<String, Object> s3 = Map.of("C", "3");
        Map<String, Object> existing = new LinkedHashMap<>();
        existing.put("schedule1", s1);
        existing.put("schedule2", s2);
        existing.put("schedule3", s3);

        Map<String, Object> result = SupabaseUserProfileStore.mergedSchedules(existing, Map.of("D", "4"));
        assertEquals(3, result.size());
        assertFalse(result.containsValue(s3), "oldest schedule3 must be dropped");
    }

    @Test
    void schedulesNullNewScheduleKeepsExisting() {
        Map<String, Object> existing = Map.of("schedule1", Map.of("STAT 400", "12345"));
        assertEquals(existing, SupabaseUserProfileStore.mergedSchedules(existing, null));
    }
}

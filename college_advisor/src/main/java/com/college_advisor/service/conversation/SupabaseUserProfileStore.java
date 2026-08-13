package com.college_advisor.service.conversation;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Array;
import java.util.*;

public class SupabaseUserProfileStore implements UserProfileStore {

    private static final Logger log = LoggerFactory.getLogger(SupabaseUserProfileStore.class);
    private static final ObjectMapper mapper = new ObjectMapper();

    private final JdbcTemplate jdbc;

    public SupabaseUserProfileStore(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public void mergeProfile(String userId, UserProfile extracted) {
        if (extracted.isEmpty()) return;  // guard: nothing to merge
        try {
            ExistingData existing = readExisting(userId);
            String mergedYear = mergedYear(existing == null ? null : existing.year(), extracted.year());
            List<String> mergedCourses = mergedCourses(
                    existing == null ? null : existing.completedCourses(), extracted.completedCourses());
            Map<String, Object> mergedPrefs = mergedPrefs(
                    existing == null ? null : existing.preferences(), extracted.preferences());
            Map<String, Object> mergedSchedules = mergedSchedules(
                    existing == null ? null : existing.schedules(), extracted.schedule());

            upsert(userId, mergedYear, mergedCourses, mergedPrefs, mergedSchedules);
            log.info("[profile-store] userId={} merged profile", userId);
        } catch (Exception e) {
            log.warn("[profile-store] userId={} merge failed: {}", userId, e.getMessage(), e);
            throw new RuntimeException(e);
        }
    }

    private ExistingData readExisting(String userId) {
        try {
            return jdbc.queryForObject(
                    "SELECT year, completed_courses, preferences::text, schedules::text " +
                    "FROM users WHERE id = ?::uuid",
                    (rs, rowNum) -> {
                        String year = rs.getString("year");
                        Array arr = rs.getArray("completed_courses");
                        List<String> courses = arr != null
                                ? new ArrayList<>(Arrays.asList((String[]) arr.getArray())) : null;
                        String prefsJson = rs.getString("preferences");
                        Map<String, Object> prefs = null;
                        if (prefsJson != null) {
                            try { prefs = mapper.readValue(prefsJson, new TypeReference<>() {}); }
                            catch (Exception ex) { throw new java.sql.SQLException(ex); }
                        }
                        String schedJson = rs.getString("schedules");
                        Map<String, Object> scheds = null;
                        if (schedJson != null) {
                            try { scheds = mapper.readValue(schedJson, new TypeReference<>() {}); }
                            catch (Exception ex) { throw new java.sql.SQLException(ex); }
                        }
                        return new ExistingData(year, courses, prefs, scheds);
                    }, userId);
        } catch (EmptyResultDataAccessException e) {
            return null;
        }
    }

    private void upsert(String userId, String year, List<String> courses,
                        Map<String, Object> prefs, Map<String, Object> schedules) throws Exception {
        String prefsJson   = prefs     != null ? mapper.writeValueAsString(prefs)     : null;
        String schedJson   = schedules != null ? mapper.writeValueAsString(schedules) : null;

        jdbc.execute((java.sql.Connection con) -> {
            String sql = "INSERT INTO users (id, year, completed_courses, preferences, schedules) " +
                         "VALUES (?::uuid, ?, ?, ?::jsonb, ?::jsonb) " +
                         "ON CONFLICT (id) DO UPDATE SET " +
                         "  year = EXCLUDED.year, " +
                         "  completed_courses = EXCLUDED.completed_courses, " +
                         "  preferences = EXCLUDED.preferences, " +
                         "  schedules = EXCLUDED.schedules";
            try (java.sql.PreparedStatement ps = con.prepareStatement(sql)) {
                ps.setString(1, userId);
                ps.setString(2, year);
                if (courses != null && !courses.isEmpty()) {
                    ps.setArray(3, con.createArrayOf("text", courses.toArray(new String[0])));
                } else {
                    ps.setNull(3, java.sql.Types.ARRAY);
                }
                ps.setString(4, prefsJson);
                ps.setString(5, schedJson);
                ps.executeUpdate();
            }
            return null;
        });
    }

    // ── package-private static merge helpers ─────────────────────────────────

    static String mergedYear(String existing, String extracted) {
        return extracted != null ? extracted : existing;
    }

    static List<String> mergedCourses(List<String> existing, List<String> extracted) {
        if (extracted == null) return existing;
        Set<String> set = new LinkedHashSet<>();
        if (existing != null) set.addAll(existing);
        set.addAll(extracted);
        return new ArrayList<>(set);
    }

    static Map<String, Object> mergedPrefs(Map<String, Object> existing, Map<String, Object> extracted) {
        if (extracted == null) return existing;
        if (existing  == null || existing.isEmpty())  return extracted;
        Map<String, Object> merged = new LinkedHashMap<>(existing);
        extracted.forEach((k, v) -> { if (v != null) merged.put(k, v); });
        return merged;
    }

    /**
     * Pushes newSchedule into the slot1 position, shifting existing 1→2, 2→3.
     * slot3 is always dropped — the store intentionally keeps at most 3 schedules.
     */
    static Map<String, Object> mergedSchedules(Map<String, Object> existing, Map<String, Object> newSchedule) {
        if (newSchedule == null) return existing;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("schedule1", newSchedule);
        if (existing != null) {
            Object s1 = existing.get("schedule1");
            Object s2 = existing.get("schedule2");
            if (s1 != null) result.put("schedule2", s1);
            if (s2 != null) result.put("schedule3", s2);
        }
        return result;
    }

    private record ExistingData(String year, List<String> completedCourses,
                                Map<String, Object> preferences, Map<String, Object> schedules) {}
}

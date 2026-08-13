package com.college_advisor.service.graph.state;

import java.io.Serializable;
import java.util.List;

/**
 * Student scheduling and course preferences extracted by the Planner from user input.
 *
 * Each field is wrapped in PreferenceField to track whether it was explicitly stated
 * by the student (autoFilled=false) or inferred as a default (autoFilled=true).
 *
 * A null field means the dimension was completely unspecified and no default was applied.
 *
 * Relaxation rule (for ReactAgent SYSTEM_PROMPT):
 *   - autoFilled=true  → relax silently if needed
 *   - autoFilled=false → relax only after notifying the user
 */
public record UserPreferences(

    /** Earliest acceptable start hour (24h). e.g. 10 = no class before 10:00 AM. */
    PreferenceField<Integer> noEarlierThan,

    /** Latest acceptable start hour (24h). e.g. 18 = no class starting after 6:00 PM. */
    PreferenceField<Integer> noLaterThan,

    /** Days to avoid. e.g. ["Fri"], ["Mon", "Wed"]. */
    PreferenceField<List<String>> avoidDays,

    /** True = student wants sections with no mandatory attendance. */
    PreferenceField<Boolean> noMandatoryAttendance,

    /** Preferred workload level: "light" | "medium" | "heavy". */
    PreferenceField<String> workload,

    /** Preferred course difficulty: "Easy" | "Medium" | "Hard". */
    PreferenceField<String> difficulty,

    /** Minimum acceptable avg_gpa for a course. e.g. 3.0. */
    PreferenceField<Double> minGpa

) implements Serializable {

    /** Empty preferences — all dimensions unspecified. */
    public static UserPreferences empty() {
        return new UserPreferences(null, null, null, null, null, null, null);
    }
}

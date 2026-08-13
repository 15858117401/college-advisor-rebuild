package com.college_advisor.service.graph.state;

import java.io.Serializable;

/**
 * Wraps a single preference value with its origin.
 * autoFilled=true  → inferred by Planner as a reasonable default; may be silently relaxed.
 * autoFilled=false → explicitly stated by the student; must notify user if relaxed.
 */
public record PreferenceField<T>(T value, boolean autoFilled) implements Serializable {}

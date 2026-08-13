package com.college_advisor.service.rag;

import com.college_advisor.service.rag.dto.CourseDraft;
import com.college_advisor.service.rag.dto.CourseSectionDraft;
import com.college_advisor.service.rag.dto.ParsedCatalog;

import java.math.BigDecimal;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Parses {@code stat.md}: preamble (before first {@code # STAT NNN}) and per-course blocks.
 */
public final class StatMdParser {

    private static final Pattern FIRST_COURSE_HEADING =
            Pattern.compile("(?m)^#\\s+STAT\\s+(\\d+)\\s*[—\\-]\\s*(.+)$");

    private static final Pattern COURSE_TITLE_LINE =
            Pattern.compile("^#\\s+STAT\\s+(\\d+)\\s*[—\\-]\\s*(.+)$");

    private static final Pattern BULLET = Pattern.compile("^-\\s+([^:]+):\\s*(.*)$");

    private static final DateTimeFormatter COMPACT_TIME =
            new DateTimeFormatterBuilder()
                    .parseCaseInsensitive()
                    .appendPattern("h:mma")
                    .toFormatter(Locale.US);

    private static final Pattern TIME_RANGE = Pattern.compile(
            "(?i)(\\d{1,2}:\\d{2})\\s*(AM|PM)\\s*[–\\-]\\s*(\\d{1,2}:\\d{2})\\s*(AM|PM)");

    private StatMdParser() {}

    public static ParsedCatalog parse(String markdown) {
        String text = markdown == null ? "" : markdown;
        Matcher first = FIRST_COURSE_HEADING.matcher(text);
        if (!first.find()) {
            return new ParsedCatalog(text.trim(), List.of());
        }
        String preamble = text.substring(0, first.start()).trim();
        String rest = text.substring(first.start()).trim();
        String[] rawBlocks = rest.split("\\R---\\R");
        List<CourseDraft> courses = new ArrayList<>();
        for (String raw : rawBlocks) {
            String block = raw.strip();
            if (block.isEmpty()) {
                continue;
            }
            Matcher m = COURSE_TITLE_LINE.matcher(block.lines().findFirst().orElse(""));
            if (!m.matches()) {
                continue;
            }
            CourseDraft course = parseCourseBlock(block);
            if (course != null) {
                courses.add(course);
            }
        }
        return new ParsedCatalog(preamble, courses);
    }

    private static CourseDraft parseCourseBlock(String block) {
        List<String> lines = block.lines().toList();
        if (lines.isEmpty()) {
            return null;
        }
        Matcher title = COURSE_TITLE_LINE.matcher(lines.get(0).strip());
        if (!title.matches()) {
            return null;
        }
        String courseCode = "STAT " + title.group(1).strip();
        String name = title.group(2).strip();

        String role = null;
        String credits = null;
        String prerequisites = null;
        String description = null;
        StringBuilder descriptionTail = new StringBuilder();

        int i = 1;
        while (i < lines.size()) {
            String line = lines.get(i);
            if (line.startsWith("##")) {
                break;
            }
            Matcher bm = BULLET.matcher(line);
            if (bm.matches()) {
                String key = bm.group(1).strip().toLowerCase(Locale.ROOT);
                String value = bm.group(2).strip();
                switch (key) {
                    case "role" -> role = emptyToNull(value);
                    case "credits" -> credits = emptyToNull(value);
                    case "prerequisites" -> prerequisites = dashToNull(value);
                    case "description" -> description = emptyToNull(value);
                    case "term", "same_as", "schedule_url" ->
                            appendTail(descriptionTail, key, value);
                    default -> appendTail(descriptionTail, key, value);
                }
            }
            i++;
        }

        String fullDescription = joinDescription(description, descriptionTail);

        List<CourseSectionDraft> sections = List.of();
        BigDecimal avgGpa = null;
        String difficulty = null;
        String workload = null;
        String assessment = null;
        Boolean attendance = null;
        List<String> tags = List.of();

        while (i < lines.size()) {
            String line = lines.get(i).strip();
            if (line.equals("## Sections")) {
                ParsedSectionBlock pb = parseSectionsTable(lines, i + 1);
                sections = pb.sections();
                i = pb.nextIndex();
                continue;
            }
            if (line.startsWith("## Student Info")) {
                StudentInfo si = parseStudentInfo(lines, i + 1);
                avgGpa = si.avgGpa();
                difficulty = si.difficulty();
                workload = si.workload();
                assessment = si.assessment();
                attendance = si.attendance();
                i = si.nextIndex();
                continue;
            }
            if (line.equals("## Tags")) {
                TagBlock tb = parseTags(lines, i + 1);
                tags = tb.tags();
                i = tb.nextIndex();
                continue;
            }
            i++;
        }

        return new CourseDraft(
                courseCode,
                name,
                role,
                credits,
                prerequisites,
                fullDescription,
                tags,
                avgGpa,
                difficulty,
                workload,
                assessment,
                attendance,
                sections
        );
    }

    private static String joinDescription(String base, StringBuilder tail) {
        if (tail.isEmpty()) {
            return base;
        }
        if (base == null || base.isBlank()) {
            return tail.toString().strip();
        }
        return base.strip() + "\n\n" + tail.toString().strip();
    }

    private static void appendTail(StringBuilder tail, String key, String value) {
        if (value == null || value.isBlank() || "—".equals(value.strip())) {
            return;
        }
        if (!tail.isEmpty()) {
            tail.append("\n\n");
        }
        tail.append(key).append(": ").append(value.strip());
    }

    private static ParsedSectionBlock parseSectionsTable(List<String> lines, int start) {
        int i = start;
        while (i < lines.size()) {
            String s = lines.get(i).strip();
            if (s.startsWith("##")) {
                return new ParsedSectionBlock(List.of(), i);
            }
            if (s.startsWith("|")) {
                break;
            }
            if (s.startsWith(">")) {
                i++;
                continue;
            }
            if (s.isEmpty()) {
                i++;
                continue;
            }
            i++;
        }
        if (i >= lines.size() || !lines.get(i).strip().startsWith("|")) {
            return new ParsedSectionBlock(List.of(), i);
        }
        i++;
        if (i < lines.size() && lines.get(i).strip().startsWith("|") && lines.get(i).contains("---")) {
            i++;
        }
        List<CourseSectionDraft> rows = new ArrayList<>();
        while (i < lines.size()) {
            String row = lines.get(i).strip();
            if (row.isEmpty()) {
                i++;
                break;
            }
            if (row.startsWith("##")) {
                break;
            }
            if (!row.startsWith("|")) {
                break;
            }
            CourseSectionDraft cell = parseSectionRow(row);
            if (cell != null) {
                rows.add(cell);
            }
            i++;
        }
        return new ParsedSectionBlock(rows, i);
    }

    private static CourseSectionDraft parseSectionRow(String row) {
        String[] raw = row.split("\\|", -1);
        if (raw.length < 9) {
            return null;
        }
        List<String> cells = new ArrayList<>();
        for (int k = 1; k < raw.length - 1; k++) {
            cells.add(raw[k].strip());
        }
        if (cells.size() < 7) {
            return null;
        }
        String type = cells.get(0);
        String section = cells.get(1);
        String crn = cells.get(2);
        String days = cells.get(3);
        String timeStr = cells.get(4);
        String location = cells.get(5);
        String instructor = cells.get(6);

        LocalTime[] range = parseTimeRange(timeStr);
        return new CourseSectionDraft(
                emptyToNull(type),
                emptyToNull(section),
                emptyToNull(crn),
                emptyToNull(days),
                timeStr,
                range == null ? null : range[0],
                range == null ? null : range[1],
                emptyToNull(location),
                emptyToNull(instructor)
        );
    }

    private static LocalTime[] parseTimeRange(String timeStr) {
        if (timeStr == null || timeStr.isBlank() || timeStr.contains("ARRANGED")) {
            return null;
        }
        Matcher m = TIME_RANGE.matcher(timeStr.replace('–', '-'));
        if (!m.find()) {
            return null;
        }
        try {
            LocalTime start = LocalTime.parse(m.group(1).strip() + m.group(2).toUpperCase(Locale.ROOT), COMPACT_TIME);
            LocalTime end = LocalTime.parse(m.group(3).strip() + m.group(4).toUpperCase(Locale.ROOT), COMPACT_TIME);
            return new LocalTime[] {start, end};
        } catch (DateTimeParseException e) {
            return null;
        }
    }

    private static StudentInfo parseStudentInfo(List<String> lines, int start) {
        BigDecimal gpa = null;
        String difficulty = null;
        String workload = null;
        String assessment = null;
        Boolean attendance = null;
        int i = start;
        for (; i < lines.size(); i++) {
            String line = lines.get(i);
            if (line.startsWith("##")) {
                break;
            }
            Matcher bm = BULLET.matcher(line.strip());
            if (!bm.matches()) {
                continue;
            }
            String key = bm.group(1).strip().toLowerCase(Locale.ROOT);
            String value = bm.group(2).strip();
            switch (key) {
                case "avg_gpa" -> gpa = parseGpa(value);
                case "difficulty" -> difficulty = emptyToNull(value);
                case "workload_hrs_per_week" -> workload = emptyToNull(value);
                case "assessment_style" -> assessment = emptyToNull(value);
                case "attendance_required" -> attendance = parseYesNo(value);
                default -> { }
            }
        }
        return new StudentInfo(gpa, difficulty, workload, assessment, attendance, i);
    }

    private static BigDecimal parseGpa(String value) {
        try {
            return new BigDecimal(value.strip());
        } catch (Exception e) {
            return null;
        }
    }

    private static Boolean parseYesNo(String value) {
        String v = value.strip().toLowerCase(Locale.ROOT);
        if (v.equals("yes") || v.equals("true")) {
            return Boolean.TRUE;
        }
        if (v.equals("no") || v.equals("false")) {
            return Boolean.FALSE;
        }
        return null;
    }

    private static TagBlock parseTags(List<String> lines, int start) {
        StringBuilder sb = new StringBuilder();
        int i = start;
        for (; i < lines.size(); i++) {
            String line = lines.get(i).strip();
            if (line.startsWith("##") || line.startsWith("---")) {
                break;
            }
            if (line.isEmpty()) {
                if (!sb.isEmpty()) {
                    i++;
                    break;
                }
                continue;
            }
            if (!sb.isEmpty()) {
                sb.append(' ');
            }
            sb.append(line);
        }
        List<String> tags = Arrays.stream(sb.toString().split(","))
                .map(String::strip)
                .filter(s -> !s.isEmpty())
                .toList();
        return new TagBlock(tags, i);
    }

    private static String emptyToNull(String s) {
        if (s == null || s.isBlank() || "—".equals(s.strip())) {
            return null;
        }
        return s.strip();
    }

    private static String dashToNull(String s) {
        if (s == null || s.isBlank() || "—".equals(s.strip())) {
            return null;
        }
        return s.strip();
    }

    private record ParsedSectionBlock(List<CourseSectionDraft> sections, int nextIndex) {}

    private record StudentInfo(
            BigDecimal avgGpa,
            String difficulty,
            String workload,
            String assessment,
            Boolean attendance,
            int nextIndex
    ) {}

    private record TagBlock(List<String> tags, int nextIndex) {}
}

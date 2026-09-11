---
name: scheduling
description: Build or revise a UIUC course schedule for the current semester.
---

# Semester Scheduling

Use this workflow for a personalized semester schedule. Adapt the work to the request: a student supplying a fixed course list needs section selection, while a student starting with preferences also needs course discovery. Reuse facts already retrieved in the current run.

## Understand the request

Identify the target semester, requested or fixed courses, credit target, unavailable days and times, and other preferences. Distinguish hard requirements from preferences using the student's wording. Use completed conversation context to resolve references and the explicit current request to establish what is wanted now. Follow the base prompt's profile and scenario precedence.

If missing information prevents a supported schedule, ask one concise question about the most consequential missing fact. Do not invent a credit target, completed coursework, or semester. Ask through the normal advising response; do not assume the shared Clarify transition is implemented.

Only Spring 2026 section data is available. Do not automatically interpret an ambiguous "this semester" as Spring 2026. If the target term is unresolved, ask which semester the student means. For another semester, explain that a verified timetable is unavailable; any supported course recommendations must remain provisional, without invented availability, sections, CRNs, instructors, or meeting times.

## Identify academic needs

For scheduling toward a degree, identify the student's exact program and relevant unmet requirements before choosing courses. Use `find_degree_programs` when the program needs resolution, then `major_graduation_requirement` for major requirements and `general_education_graduation_requirement` when LAS general education requirements are in scope. Do not perform a broad graduation audit for a fixed course list or a request limited to one requirement type. Stored major requirements are for 2026–2027; do not present them as verified requirements for another catalog year or substitute a general-major document for missing concentration rules.

Compare the applicable requirements with confirmed completed credit to identify useful next courses and remaining requirement categories. Check course details when needed to establish how completed coursework counts. Do not assume that pending transfer credit, in-progress work, or unknown grades satisfy a requirement. Prioritize required courses and prerequisite sequences relevant to the student's goals without counting overlapping or restricted credit twice.

Establish the GPA preference as part of these academic needs, and carry it into course and section selection:

- If the student says nothing about GPA, prefer higher historical course GPA among choices that meet their request, hard constraints, and academic needs. Prefer higher historical instructor GPA when selecting otherwise suitable sections of a course.
- If the student explicitly does not care about GPA, do not use GPA to filter, rank, or explain choices, and skip instructor GPA lookups unless they separately request those statistics.
- If the student states a GPA preference or requirement, follow it instead of the default. Apply a hard threshold only when they actually request one. Distinguish a course's historical average, an instructor's historical average, and the student's own GPA; a target student GPA is not a course-average threshold or an outcome that can be guaranteed. Ask if an ambiguous GPA requirement would change the schedule.
- Use `get_course_details` for historical course `overall_gpa` and `get_course_instructor_gpas` for historical course–instructor averages when this preference calls for them. Missing GPA is unknown, not low; it cannot establish that a hard GPA threshold is met. These averages do not identify a particular current section or predict the student's grade, workload, or teaching quality.

## Find eligible courses

Use `find_courses` to discover courses matching unmet requirements, interests, or stated conditions. Omit `subjects` to search across stored departments unless a department restriction is useful or requested; the major does not limit where relevant courses can come from. Rewrite semantic queries around course content. Search filters combine with AND, so use separate searches for alternatives. Use a minimum GPA filter only for an explicit applicable course-GPA threshold, not an invented cutoff for the default preference.

The discovery tool returns course codes and credit strings only. Use `get_course_details` to verify shortlisted courses' prerequisites, credits, credit restrictions, general education categories, and relevant GPA evidence. The `find_courses` filter `prerequisite_course` is only a catalog-text match, not an eligibility check. For a fixed course list, skip discovery and retrieve its details directly.

Exclude courses the student cannot take based on known prerequisites or restrictions, and do not reselect completed courses without a supported reason. Apply the base prompt's prerequisite and concurrent-registration rules. Keep uncertain eligibility explicit rather than presenting it as confirmed. For variable-credit courses, distinguish the proposed credit choice from a verified section-specific credit value.

## Find feasible sections

Retrieve sections for shortlisted eligible courses with `get_course_sections`. Read each course's result independently: an error is unavailable evidence, while an empty successful result supplies no sections for the supported semester. Do not treat either as a verified scheduling option.

Consider lecture, discussion, laboratory, and other required components together. Returned section rows do not establish registration linkage, seat availability, or all enrollment restrictions. Do not assume that similar section labels prove a valid pairing; identify an inferred pairing as provisional and requiring confirmation. Never promise that a seat is open.

Check every returned meeting against the student's unavailable periods and other selected meetings. Expand meeting-day abbreviations carefully and inspect every time interval, including multiple meetings in one row. An overlap occurs on a shared day when one meeting starts before the other ends and ends after the other starts. Back-to-back times do not overlap, but must respect any requested transition buffer. Do not invent travel times from locations. TBA or unparseable meetings are unknown, not proof of an asynchronous or conflict-free option.

Use the GPA preference established under academic needs when comparing feasible sections. Match instructor GPA evidence to the same course and a confidently identified instructor; do not force an ambiguous abbreviated-name match, transfer another instructor's GPA, or invent a combined GPA for multiple instructors. Load `professor-research` only when teaching style, reputation, or student experiences matter to the request.

## Assemble and verify the schedule

Build one complete combination within the requested credit and workload limits. Count each course's credits once even when it needs several section components. Recheck requirement fit, prerequisites, component pairings, every meeting, hard constraints, and the GPA preference across the whole combination.

Resolve conflicts by trying other sections of suitable courses before replacing courses. If replacement is needed and the student allows it, choose another eligible course serving the relevant academic need, retrieve its details and sections, and check the complete combination again. Never silently replace a required or fixed course or relax a hard constraint. A failed shortlist does not prove that no feasible schedule exists.

If a blocking fact or conflicting requirement remains, explain it and ask one targeted question needed to continue. A partially verified proposal must be labeled provisional and must not be called a complete, feasible schedule.

Keep calls focused on candidates that could affect the result. Batch at most five course codes per `get_course_details` call, three per `get_course_sections` call, and two per `get_course_instructor_gpas` call. Group independent tool calls in the same model round where possible, reuse retrieved evidence, and stop searching once one supported schedule meets the request.

## Hand off the schedule

Provide Compose Response with one proposed schedule containing course codes, proposed credits, selected section identifiers and CRNs, instructors, and meeting days/times where supported. Include the total credits, a brief explanation of how the choices meet academic needs and preferences, and any essential eligibility, linkage, term, or missing-data caveat. Keep supporting GPA claims correctly labeled as historical evidence. Compose Response owns final formatting and concision; do not add unrequested alternatives or a second day-by-day version.

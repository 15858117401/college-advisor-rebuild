---
name: course_and_section_recommendation
description: Find courses matching the user's conditions, retrieve their Spring 2026 sections, and attach historical course-instructor GPA data.
---

# Course and Section Recommendation

Use this workflow when the student wants course recommendations together with the
sections offered in the currently loaded semester and the available historical GPA
data for those sections' instructors.

This workflow has no connection to graduation requirements. Do not call
`find_degree_programs`, `major_graduation_requirement`, or
`general_education_graduation_requirement` while following it, and do not claim that
a recommended course satisfies a degree requirement.

## Workflow

### 1. Find courses matching the request

Split the request into cohesive condition groups. Each group requires one separate
`find_courses` call. All conditions inside one group must apply to every course in
that group. Do not merge groups with different conditions or requested quantities.

For example:

- Two statistics courses about programming are one group and require one call.
- One statistics course and one US Minority course are two groups and require two
  calls.

Use the user's subject, topic, Gen Ed category, course level, credit, prerequisite,
and GPA conditions as applicable. If the user supplies explicit course codes, treat
those courses as the matched set and continue to the section step. If a search
returns `[]`, report that the knowledge base has no courses matching that group and
do not repeat the same search or relax its conditions.

### 2. Retrieve the available sections

Call `get_course_sections` for the matched course codes, batching no more than three
course codes per call. The section tool contains only Spring 2026 data, so describe
the returned sections as Spring 2026 sections.

Keep the section identifier and type, CRN, instructor, days, start and end times,
and location. An empty section list means that no Spring 2026 section was returned
for that course. Do not invent another term, section, instructor, meeting time, or
location.

### 3. Retrieve and match instructor GPA data

For courses that have returned sections, call `get_course_instructor_gpas`, batching
no more than two course codes per call. For each section, match its listed instructor
only against GPA records for the same course. Attach the GPA only when the instructor
can be identified confidently; otherwise mark the historical instructor GPA as
unavailable.

The returned GPA is the historical average for that course and instructor. It is
not a GPA for the specific Spring 2026 section or a prediction of the student's
grade. Multiple sections taught by the same instructor may therefore show the same
historical course-instructor GPA. Missing GPA data is unknown, not zero.

### 4. Return the recommendations

Preserve the course order returned by `find_courses`. Honor the requested number of
courses when enough matched courses with sections are available; return fewer rather
than padding the result when there are not enough.

For each recommended course, provide:

- Course code and credits.
- The Spring 2026 sections returned for that course.
- For each section: section identifier and type, CRN, instructor, meeting days and
  times, location, and matched historical course-instructor GPA when available.

If matched courses have no Spring 2026 sections, say so directly. If sections exist
but instructor GPA data is missing, keep the sections and label the GPA as
unavailable. Do not add graduation-requirement analysis or unrelated recommendations.

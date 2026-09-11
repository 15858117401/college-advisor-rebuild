---
name: planner
description: Plan UIUC major requirements semester by semester toward graduation, usually with two or three major courses per semester.
---

# Planner Skill

Use this skill for a long-term, semester-by-semester major course plan. Plan only the major requirements and their necessary prerequisites. Do not retrieve LAS general education requirements or add general education courses to fill semesters. This is a major-completion plan, not a complete graduation audit or a section timetable.

## Check the major requirements

Identify the student's exact major or concentration, using `find_degree_programs` when necessary, then retrieve its requirements with `major_graduation_requirement` before planning. Follow the base prompt's program-resolution and profile/scenario rules. If the intended program is ambiguous or its requirements are unavailable, ask one targeted question or explain the limitation; do not substitute another program's requirements. Identify the stored 2026–2027 catalog year rather than claiming another year's requirements are verified.

Compare the requirements with confirmed completed coursework to identify the remaining required courses, elective groups, and credit requirements. Keep pending transfer credit and in-progress courses separate from completed credit. If missing academic history prevents identifying what remains, ask one targeted question instead of assuming the student starts from zero. Use the student's stated starting term, graduation target, and workload limits when available.

## Find the remaining courses

Use `get_course_details` for the remaining required courses and their prerequisites. Use `find_courses` only when a requirement offers elective choices or needs course discovery, then verify selected candidates with `get_course_details`. Select concrete courses that satisfy the stored requirement and the student's preferences. Do not replace a missing requirement with an invented elective or count restricted or overlapping credit twice.

The major determines the requirements, not the course subject. Include required courses from other departments and any necessary prerequisite courses; label prerequisite-only work when it does not itself fulfill a major requirement. Check prerequisite chains, credits, restrictions, and any minimum-grade or permission conditions. Reuse retrieved information and batch up to five course codes per `get_course_details` call.

## Build the semester-by-semester plan

Place prerequisite courses in earlier semesters than their dependent courses, unless retrieved catalog text permits concurrent registration or the student confirms the required permission. Treat completion of planned earlier courses as a condition of progressing to later courses. Prioritize courses that unlock later requirements, then distribute the remaining requirements and electives.

Usually plan two or three major-related courses per semester. This is a default pace, not a reason to violate the student's limits or force an unnecessary course into a term. A final term or a prerequisite bottleneck may need fewer courses. Check actual credit totals as well as course counts. If the requested graduation target cannot be met within the student's constraints, explain what remains or why another term is needed instead of compressing prerequisite chains or silently overloading a semester.

Use the supplied term names when available; otherwise label rows Semester 1, Semester 2, and so on. Do not add summer terms unless the student requests them. Continue until all supported remaining major requirements are covered, and clearly identify any unresolved requirement that prevents confirming major completion. The six-choice limit from course recommendations does not apply to this plan.

Do not call section or instructor-research tools for this workflow. Future course availability is unknown: semester placements are a proposed academic sequence, not confirmed offerings. Do not invent sections, CRNs, meeting times, locations, or future instructors.

Provide Compose Response with the complete semester-to-course assignments, course codes and titles, verified planned credits, and brief notes on prerequisite order or requirement fulfillment. State that the plan covers the major only and that future offerings need verification; do not claim that completing it alone satisfies every graduation requirement. Compose Response owns the final table formatting and concision.

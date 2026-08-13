# Skill: Minimal Graduation

## Triggers
easy, light workload, low effort, no attendance, online, afternoon, 混毕业, 轻松毕业, minimal, stress-free, chill semester

## Goal
Help student graduate with minimum friction. Satisfy all degree requirements using the
lowest-effort path — least workload, fewest attendance obligations, highest GPA courses.

## Degree Structure (UIUC Statistics Major)
- **Intro sequence (choose 1):** STAT 107, STAT 200, or STAT 212
- **Required core (all 4 required):** STAT 400, STAT 410, STAT 425, STAT 426
- **Electives (choose 4):** any 4 from the courses tagged role='elective' in the database

## Strategy
- Required core (STAT 400, 410, 425, 426) cannot be avoided — acknowledge this to student upfront
- For the intro requirement (choose 1 from STAT 107/200/212), recommend the easiest option:
  - Primary sort: workload_hrs_per_week ASC
  - Tiebreak: avg_gpa DESC, then attendance_required=false preferred
- For electives (choose 4 from role='elective' pool), optimize in this order:
  1. workload_hrs_per_week ASC (lowest effort first)
  2. attendance_required = false preferred
  3. avg_gpa DESC (higher GPA buffer)
- If student mentions time preference (afternoon, no early morning), call getCourseSections with time filter
- If student mentions topic interest, filter elective pool by topic only if workload is still acceptable
- Pre-fetched data is already provided below — do NOT re-query these; use them directly

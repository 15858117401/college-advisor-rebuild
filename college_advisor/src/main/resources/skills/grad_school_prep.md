# Skill: Grad School Prep

## Triggers
grad school, PhD, master's, doctoral, research, 考研, 申请研究生, graduate application

## Goal
Build a course portfolio that strengthens the student's graduate school application.
Focus on theoretical depth, mathematical rigor, and professor reputation.

## Degree Structure (UIUC Statistics Major)
- **Intro sequence (choose 1):** STAT 107, STAT 200, or STAT 212
- **Required core (all 4 required):** STAT 400, STAT 410, STAT 425, STAT 426
- **Electives (choose 4):** any 4 from the courses tagged role='elective' in the database

## Strategy
- Required core (STAT 400, 410, 425, 426) is the foundation — these MUST appear in the plan
- For the intro requirement (choose 1 from STAT 107/200/212), recommend STAT 212 if student has
  math background; it signals rigor to graduate admissions committees
- For electives (choose 4 from role='elective' pool), prioritize:
  1. difficulty IN ('Medium', 'Hard') — theory-heavy courses signal academic rigor
  2. avg_gpa >= 3.0 — avoid GPA traps unless student is confident
  3. If two courses are similar difficulty, prefer higher avg_gpa (safety buffer)
- Professor reputation matters — if student asks, use searchRateMyProfessor to check instructors
- Advise student that strong performance in STAT 400 and STAT 410 is critical for rec letters
- Balance the portfolio: include at least one probability course, one mathematical statistics course,
  and one computational/applied course to show breadth
- Pre-fetched data is already provided below — do NOT re-query these; use them directly

# User Profile

This directory will contain the User Profile data for the UIUC college-advising application. For now, keep the User Profile as simple as possible and use only this schema:

```json
{
  "major": "Mathematics - Applied Mathematics",
  "completed_courses": ["MATH 220", "MATH 231", "RHET 105"],
  "cumulative_gpa": 3.25,
  "major_gpa": 3.10
}
```

`major` is one string that includes any concentration or similar program detail. `completed_courses` is an array containing only the course ID for every completed course, including General Education courses. `cumulative_gpa` and `major_gpa` are the only GPA fields. This is the complete planned Profile model for now; do not add other fields or functionality unless explicitly requested later.

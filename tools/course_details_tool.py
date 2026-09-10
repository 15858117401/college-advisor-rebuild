import re
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from Supabase.import_stat_resources import create_supabase_client


COURSE_CODE_PATTERN = re.compile(r"^([A-Za-z]{2,4})\s*(\d{3}[A-Za-z]?)$", re.IGNORECASE)
COURSE_SELECT_FIELDS = (
    "course_code,subject,course_number,course_name,credits,description,"
    "prerequisites,credit_restrictions,gen_ed,total_students,total_sections,"
    "overall_gpa"
)


class GetCourseDetailsInput(BaseModel):
    course_codes: list[str] = Field(
        min_length=1,
        max_length=5,
        description=(
            "One to five explicit UIUC course codes, such as "
            "['MATH 416'] or ['ECON 302', 'STAT 400']."
        ),
    )

    @field_validator("course_codes")
    @classmethod
    def normalize_course_codes(cls, course_codes: list[str]) -> list[str]:
        normalized: list[str] = []
        for course_code in course_codes:
            match = COURSE_CODE_PATTERN.fullmatch(course_code.strip())
            if match is None:
                raise ValueError(
                    f"invalid course code {course_code!r}; "
                    "expected a value like 'MATH 416'"
                )
            normalized.append(f"{match.group(1).upper()} {match.group(2).upper()}")
        return normalized


@tool("get_course_details", args_schema=GetCourseDetailsInput)
def get_course_details(course_codes: list[str]) -> list[dict[str, Any]]:
    """Get catalog details for one to five specific stored UIUC courses.

    Use this when explicit course codes are known. Do not use this to
    discover courses from natural-language topics or conditions.
    """
    unique_course_codes = list(dict.fromkeys(course_codes))
    response = (
        create_supabase_client()
        .table("courses")
        .select(COURSE_SELECT_FIELDS)
        .in_("course_code", unique_course_codes)
        .execute()
    )
    courses_by_code = {
        row["course_code"]: row
        for row in (response.data or [])
    }

    results: list[dict[str, Any]] = []
    for course_code in course_codes:
        course = courses_by_code.get(course_code)
        if course is None:
            results.append({"course_code": course_code, "message": "no such course"})
        else:
            results.append(dict(course))
    return results


__all__ = ["GetCourseDetailsInput", "get_course_details"]

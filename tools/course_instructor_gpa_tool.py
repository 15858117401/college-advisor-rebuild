import re
from collections import defaultdict

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from Supabase.import_stat_resources import create_supabase_client
from Supabase.resource_queries import fetch_all_rows


COURSE_CODE_PATTERN = re.compile(r"^([A-Za-z]{2,4})\s*(\d{3}[A-Za-z]?)$")


class GetCourseInstructorGpasInput(BaseModel):
    course_codes: list[str] = Field(
        min_length=1,
        max_length=2,
        description="One or two UIUC course codes, such as MATH 416 or ECON 302.",
    )

    @field_validator("course_codes")
    @classmethod
    def normalize_course_codes(cls, values: list[str]) -> list[str]:
        codes = []
        for value in values:
            match = COURSE_CODE_PATTERN.fullmatch(value.strip())
            if match is None:
                raise ValueError(f"invalid course code {value!r}; expected a value like 'MATH 416'")
            codes.append(f"{match.group(1).upper()} {match.group(2).upper()}")
        return codes


@tool("get_course_instructor_gpas", args_schema=GetCourseInstructorGpasInput)
def get_course_instructor_gpas(course_codes: list[str]) -> list[dict]:
    """Get historical average GPA by instructor for one or two UIUC courses.

    Multiple database rows for the same course and instructor are averaged.
    The statistics do not identify specific sections or academic terms.
    Valid course codes without stored statistics return no GPA information.
    """
    unique_course_codes = list(dict.fromkeys(course_codes))
    client = create_supabase_client()
    rows = fetch_all_rows(lambda: (
        client.table("course_instructor_stats")
        .select("course_code,instructor_name,instructor_avg_gpa")
        .in_("course_code", unique_course_codes)
        .order("id")
    ))

    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        gpa = row.get("instructor_avg_gpa")
        if gpa is None:
            continue
        grouped[row["course_code"]][row["instructor_name"]].append(float(gpa))

    results = []
    for course_code in course_codes:
        instructors = []
        for name, gpas in grouped[course_code].items():
            instructors.append(
                {
                    "name": name,
                    "average_gpa": round(sum(gpas) / len(gpas), 3),
                }
            )
        instructors.sort(key=lambda item: (-item["average_gpa"], item["name"]))

        result = {"course_code": course_code, "instructors": instructors}
        if not instructors:
            result["message"] = "no instructor GPA information"
        results.append(result)
    return results


__all__ = ["get_course_instructor_gpas"]

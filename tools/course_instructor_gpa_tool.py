import re
from collections import defaultdict
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from Supabase.import_stat_resources import create_supabase_client


COURSE_CODE_PATTERN = re.compile(r"^STAT\s*(\d{3})$", re.IGNORECASE)


@tool("get_course_instructor_gpas")
def get_course_instructor_gpas(
    course_codes: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=2,
            description="One or two explicit STAT course codes.",
        ),
    ],
) -> list[dict]:
    """Get historical average GPA by instructor for one or two STAT courses.

    Multiple database rows for the same course and instructor are averaged.
    The statistics do not identify specific sections or academic terms.
    """
    normalized_codes = []
    for course_code in course_codes:
        match = COURSE_CODE_PATTERN.fullmatch(course_code.strip())
        if match is None:
            raise ValueError(
                f"invalid course code {course_code!r}; expected a value like 'STAT 420'"
            )
        normalized_codes.append(f"STAT {match.group(1)}")
    course_codes = normalized_codes

    unique_course_codes = list(dict.fromkeys(course_codes))
    response = (
        create_supabase_client()
        .table("course_instructor_stats")
        .select("course_code,instructor_name,instructor_avg_gpa")
        .in_("course_code", unique_course_codes)
        .execute()
    )

    grouped = defaultdict(lambda: defaultdict(list))
    for row in response.data or []:
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

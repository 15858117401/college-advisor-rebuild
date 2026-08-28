import json
import math
import re
from typing import Any, Literal, Self

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, model_validator

from client.embedding_client import embed_texts
from Supabase.import_stat_resources import create_supabase_client


COURSE_FIELDS = (
    "course_code,course_number,credits,prerequisites,gen_ed,overall_gpa"
)
COURSE_CODE_PATTERN = re.compile(r"\b([A-Za-z]{2,4})\s*(\d{3}[A-Za-z]?)\b")


class FindCoursesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description_query: str | None = Field(
        default=None,
        description="An already-rewritten query for semantic description matching.",
    )
    min_course_number: int | None = Field(default=None, ge=0, le=999)
    max_course_number: int | None = Field(default=None, ge=0, le=999)
    credit_hours: int | None = Field(default=None, ge=0, le=99)
    gen_ed: Literal[
        "Quantitative Reasoning I",
        "Quantitative Reasoning II",
    ] | None = None
    prerequisite_course: str | None = None
    min_overall_gpa: float | None = Field(default=None, ge=0.0, le=4.0)
    max_overall_gpa: float | None = Field(default=None, ge=0.0, le=4.0)
    semantic_limit: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def validate_conditions(self) -> Self:
        if self.prerequisite_course is not None:
            match = COURSE_CODE_PATTERN.fullmatch(self.prerequisite_course.strip())
            if match is None:
                raise ValueError(
                    "invalid prerequisite course; expected 'STAT 400' or 'STAT400'"
                )
            self.prerequisite_course = (
                f"{match.group(1).upper()} {match.group(2).upper()}"
            )
        if (
            self.min_course_number is not None
            and self.max_course_number is not None
            and self.min_course_number > self.max_course_number
        ):
            raise ValueError("min_course_number cannot exceed max_course_number")
        if (
            self.min_overall_gpa is not None
            and self.max_overall_gpa is not None
            and self.min_overall_gpa > self.max_overall_gpa
        ):
            raise ValueError("min_overall_gpa cannot exceed max_overall_gpa")
        conditions = self.model_dump(exclude={"semantic_limit"})
        if all(value is None for value in conditions.values()):
            raise ValueError("at least one course search condition is required")
        return self


def _matches_credit_hours(credits: str, requested: int) -> bool:
    values = [int(value) for value in re.findall(r"\d+", credits)]
    if " to " in credits.casefold():
        return values[0] <= requested <= values[1]
    return requested in values


def _matches_rules(row: dict[str, Any], criteria: dict[str, Any]) -> bool:
    number = row["course_number"]
    gpa = row["overall_gpa"]
    prerequisite_codes = COURSE_CODE_PATTERN.findall(row["prerequisites"] or "")
    listed_prerequisites = {
        f"{subject.upper()} {course_number.upper()}"
        for subject, course_number in prerequisite_codes
    }
    return (
        (
            criteria["min_course_number"] is None
            or number >= criteria["min_course_number"]
        )
        and (
            criteria["max_course_number"] is None
            or number <= criteria["max_course_number"]
        )
        and (
            criteria["credit_hours"] is None
            or _matches_credit_hours(row["credits"], criteria["credit_hours"])
        )
        and (criteria["gen_ed"] is None or row["gen_ed"] == criteria["gen_ed"])
        and (
            criteria["prerequisite_course"] is None
            or criteria["prerequisite_course"] in listed_prerequisites
        )
        and (
            gpa is None
            or criteria["min_overall_gpa"] is None
            or gpa >= criteria["min_overall_gpa"]
        )
        and (
            gpa is None
            or criteria["max_overall_gpa"] is None
            or gpa <= criteria["max_overall_gpa"]
        )
    )


def _vector(value: str | list[float]) -> list[float]:
    return json.loads(value) if isinstance(value, str) else value


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right))
    magnitude = math.sqrt(
        sum(value * value for value in left)
        * sum(value * value for value in right)
    )
    return dot_product / magnitude


def _format_results(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"course_code": row["course_code"], "credits": row["credits"]}
        for row in rows
    ]


@tool("find_courses", args_schema=FindCoursesInput)
def find_courses(
    description_query: str | None = None,
    min_course_number: int | None = None,
    max_course_number: int | None = None,
    credit_hours: int | None = None,
    gen_ed: Literal[
        "Quantitative Reasoning I",
        "Quantitative Reasoning II",
    ] | None = None,
    prerequisite_course: str | None = None,
    min_overall_gpa: float | None = None,
    max_overall_gpa: float | None = None,
    semantic_limit: int = 5,
) -> list[dict[str, str]]:
    """Find STAT courses using AND rules, then optional semantic Top-K.

    prerequisite_course accepts formats such as STAT400 or STAT 400 and matches
    a code listed in the catalog text; it does not determine student eligibility.
    The description_query is already rewritten. Returns only course_code and
    the catalog's original credits string.
    """
    criteria = locals()
    fields = COURSE_FIELDS + (",embedding" if description_query is not None else "")
    response = (
        create_supabase_client()
        .table("courses")
        .select(fields)
        .eq("subject", "STAT")
        .execute()
    )
    candidates = [
        row for row in (response.data or []) if _matches_rules(row, criteria)
    ]

    if not candidates:
        return []
    if description_query is None:
        candidates.sort(key=lambda row: row["course_number"])
        return _format_results(candidates)

    query_vector = embed_texts([description_query])[0]
    candidates.sort(
        key=lambda row: (
            -_cosine_similarity(query_vector, _vector(row["embedding"])),
            row["course_code"],
        )
    )
    return _format_results(candidates[:semantic_limit])


__all__ = ["FindCoursesInput", "find_courses"]

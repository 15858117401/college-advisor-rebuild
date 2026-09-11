import re
from typing import Literal, Self

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from client.embedding_client import embed_texts
from Supabase.import_stat_resources import create_supabase_client


COURSE_CODE_PATTERN = re.compile(r"\b([A-Za-z]{2,4})\s*(\d{3}[A-Za-z]?)\b")
GEN_ED_CATEGORIES = [
    "Advanced Composition",
    "Composition I",
    "Cultural Studies - Non-West",
    "Cultural Studies - US Minority",
    "Cultural Studies - Western",
    "Grand Challenge-Sustainability",
    "Humanities - Hist & Phil",
    "Humanities - Lit & Arts",
    "Nat Sci & Tech - Life Sciences",
    "Nat Sci & Tech - Phys Sciences",
    "Quantitative Reasoning I",
    "Quantitative Reasoning II",
    "Social & Beh Sci - Beh Sci",
    "Social & Beh Sci - Soc Sci",
    "UIUC: Ugrad Zero Credit Intern",
]
GenEdCategory = Literal[*GEN_ED_CATEGORIES]


class FindCoursesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subjects: list[str] | None = Field(
        default=None, min_length=1,
        description="Optional course subjects, e.g. ['ECON', 'MATH']. Omit to search all stored subjects.",
    )
    description_query: str | None = Field(
        default=None,
        description="An already-rewritten query for semantic description matching.",
    )
    min_course_number: int | None = Field(default=None, ge=0, le=999)
    max_course_number: int | None = Field(default=None, ge=0, le=999)
    credit_hours: int | None = Field(default=None, ge=0, le=99)
    gen_ed: GenEdCategory | None = None
    prerequisite_course: str | None = None
    min_overall_gpa: float | None = Field(default=None, ge=0.0, le=4.0)
    max_overall_gpa: float | None = Field(default=None, ge=0.0, le=4.0)

    @field_validator("gen_ed", mode="before")
    @classmethod
    def normalize_gen_ed(cls, gen_ed: object) -> object:
        return gen_ed.strip() if isinstance(gen_ed, str) else gen_ed

    @model_validator(mode="after")
    def validate_conditions(self) -> Self:
        if self.subjects is not None:
            subjects = [subject.strip().upper() for subject in self.subjects]
            if any(re.fullmatch(r"[A-Z]{2,4}", subject) is None for subject in subjects):
                raise ValueError("subjects must be course prefixes such as MATH or ECON")
            self.subjects = list(dict.fromkeys(subjects))
        if self.description_query is not None:
            self.description_query = self.description_query.strip()
            if not self.description_query:
                raise ValueError("description_query cannot be blank")
        if self.prerequisite_course is not None:
            match = COURSE_CODE_PATTERN.fullmatch(self.prerequisite_course.strip())
            if match is None:
                raise ValueError(
                    "invalid prerequisite course; expected 'MATH 241' or 'MATH241'"
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
        conditions = self.model_dump()
        if all(value is None for value in conditions.values()):
            raise ValueError("at least one course search condition is required")
        return self


def _format_results(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    return [
        {"course_code": str(row["course_code"]), "credits": str(row["credits"])}
        for row in rows
    ]


@tool("find_courses", args_schema=FindCoursesInput)
def find_courses(
    description_query: str | None = None,
    min_course_number: int | None = None,
    max_course_number: int | None = None,
    credit_hours: int | None = None,
    gen_ed: GenEdCategory | None = None,
    prerequisite_course: str | None = None,
    min_overall_gpa: float | None = None,
    max_overall_gpa: float | None = None,
    subjects: list[str] | None = None,
) -> list[dict[str, str]]:
    """Return up to five stored UIUC courses matching all supplied conditions.

    Each `find_courses` call handles exactly one cohesive course group. All supplied
    conditions apply to every course in that group and are combined with AND. If the
    user requests separate groups with different conditions or quantities, call
    `find_courses` separately once for each group. For example, "two
    programming-focused STAT courses" is one call; "one STAT course and one US
    Minority course" requires two calls. Never merge distinct groups into one call.

    prerequisite_course accepts formats such as MATH241 or MATH 241 and matches
    a code listed in the catalog text; it does not determine student eligibility.
    Omitted subjects searches all stored subjects; use subjects to narrow by department.
    A major can require courses from multiple departments.
    The description_query is already rewritten and enables semantic matching.
    Supabase performs filtering and semantic retrieval; results are always returned
    by descending historical course GPA. Returns only course_code and the catalog's
    original credits string.
    """
    query_vector = embed_texts([description_query])[0] if description_query else None
    response = create_supabase_client().rpc(
        "search_courses",
        {
            "p_query_embedding": query_vector,
            "p_subjects": subjects,
            "p_min_course_number": min_course_number,
            "p_max_course_number": max_course_number,
            "p_credit_hours": credit_hours,
            "p_gen_ed": gen_ed,
            "p_prerequisite_course": prerequisite_course,
            "p_min_overall_gpa": min_overall_gpa,
            "p_max_overall_gpa": max_overall_gpa,
        },
    ).execute()
    return _format_results(response.data or [])


__all__ = [
    "FindCoursesInput",
    "GEN_ED_CATEGORIES",
    "GenEdCategory",
    "find_courses",
]

import re
from typing import Any
from urllib.parse import urlsplit

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from client.tavily_client import search_tavily


UIUC_NAME = "University of Illinois Urbana-Champaign"
COURSE_CODE_PATTERN = re.compile(r"^([A-Za-z]{2,4})\s*(\d{3}[A-Za-z]?)$")


class ProfessorSearchInput(BaseModel):
    professor_name: str = Field(
        min_length=2,
        max_length=100,
        description="The professor's name, such as 'Albert Yu'.",
    )
    course_code: str | None = Field(
        default=None,
        description=(
            "Optional UIUC course code used to narrow reviews, such as 'MATH 416' or 'ECON 302'."
        ),
    )

    @field_validator("professor_name")
    @classmethod
    def normalize_professor_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2 or not any(character.isalpha() for character in value):
            raise ValueError("professor_name must contain at least two characters")
        return value

    @field_validator("course_code")
    @classmethod
    def normalize_course_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        match = COURSE_CODE_PATTERN.fullmatch(value.strip())
        if match is None:
            raise ValueError("invalid course code; expected a value like 'STAT 400'")
        return f"{match.group(1).upper()} {match.group(2).upper()}"


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _result_tokens(result: dict[str, Any]) -> set[str]:
    return _tokens(f"{result.get('title', '')} {result.get('content', '')}")


def _is_uiuc_reddit_url(url: str) -> bool:
    try:
        return urlsplit(url).path.casefold().startswith("/r/uiuc/")
    except ValueError:
        return False


def _envelope(
    source: str,
    query: str,
    results: list[dict[str, Any]],
    search_result: dict[str, Any],
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "source": source,
        "university": UIUC_NAME,
        "query": query,
        "results": results,
    }
    if "error" in search_result:
        response["error"] = search_result["error"]
    return response


@tool("search_rate_my_professor", args_schema=ProfessorSearchInput)
def search_rate_my_professor(
    professor_name: str, course_code: str | None = None
) -> dict[str, Any]:
    """Search Rate My Professors for a UIUC professor's ratings and reviews."""
    course_part = f' "{course_code}"' if course_code else ""
    query = (
        f'"{professor_name}" "{UIUC_NAME}"{course_part} '
        "Rate My Professors"
    )
    search_result = search_tavily(
        query,
        include_domains=["ratemyprofessors.com"],
    )
    professor_tokens = _tokens(professor_name)
    uiuc_tokens = {"illinois", "urbana", "champaign"}
    accepted_results = []
    for result in search_result["results"]:
        result_tokens = _result_tokens(result)
        identifies_uiuc = "uiuc" in result_tokens or uiuc_tokens <= result_tokens
        if professor_tokens <= result_tokens and identifies_uiuc:
            accepted_results.append(result)
    return _envelope(
        "rate_my_professors", query, accepted_results, search_result
    )


@tool("search_reddit", args_schema=ProfessorSearchInput)
def search_reddit(
    professor_name: str, course_code: str | None = None
) -> dict[str, Any]:
    """Search r/UIUC for student discussions about a UIUC professor."""
    course_part = f' "{course_code}"' if course_code else ""
    query = (
        f'"{professor_name}"{course_part} UIUC professor review '
        "site:reddit.com/r/UIUC"
    )
    search_result = search_tavily(query, include_domains=["reddit.com"])
    professor_tokens = _tokens(professor_name)
    accepted_results = [
        result
        for result in search_result["results"]
        if _is_uiuc_reddit_url(str(result.get("url", "")))
        and professor_tokens <= _result_tokens(result)
    ]
    return _envelope("reddit", query, accepted_results, search_result)


__all__ = ["ProfessorSearchInput", "search_rate_my_professor", "search_reddit"]

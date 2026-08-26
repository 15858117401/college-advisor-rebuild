import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator


COURSE_URL_TEMPLATE = (
    "https://courses.illinois.edu/schedule/2026/spring/{subject}/{number}"
)
REQUEST_TIMEOUT_SECONDS = 15
COURSE_CODE_PATTERN = re.compile(r"^([A-Za-z]{2,4})\s+(\d{3}[A-Za-z]?)$")
TIME_RANGE_PATTERN = re.compile(
    r"(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)",
    re.IGNORECASE,
)


class GetCourseSectionsInput(BaseModel):
    course_codes: list[str] = Field(
        min_length=1,
        max_length=3,
        description=(
            "One to three course codes, such as ['STAT 107'] or "
            "['STAT 107', 'STAT 200', 'STAT 400']."
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
                    f"invalid course code {course_code!r}; expected a value like 'STAT 107'"
                )
            normalized.append(f"{match.group(1).upper()} {match.group(2).upper()}")
        return normalized


class CoursePageParseError(ValueError):
    pass


class _CourseScheduleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.course_label = ""
        self.rows: list[list[str]] = []
        self.table_found = False
        self._in_course_label = False
        self._in_table = False
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if tag == "div" and {"app-label", "app-text-engage"}.issubset(classes):
            self._in_course_label = True

        if tag == "table" and attributes.get("id") == "schedule-course-table":
            self.table_found = True
            self._in_table = True
        elif self._in_table and tag == "tr":
            self._row = []
        elif self._row is not None and tag == "td":
            self._cell_parts = []
        elif self._cell_parts is not None and tag == "br":
            self._cell_parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._in_course_label:
            self._in_course_label = False

        if self._cell_parts is not None and tag == "td":
            self._row.append(" ".join("".join(self._cell_parts).split()))
            self._cell_parts = None
        elif self._row is not None and tag == "tr":
            self.rows.append(self._row)
            self._row = None
        elif self._in_table and tag == "table":
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_course_label:
            self.course_label += data
        if self._cell_parts is not None:
            self._cell_parts.append(data)


def _normalize_time(value: str) -> str:
    try:
        parsed = datetime.strptime(value.replace(" ", "").upper(), "%I:%M%p")
    except ValueError as exc:
        raise CoursePageParseError(f"invalid meeting time: {value!r}")
    return parsed.strftime("%H:%M")


def _parse_time_range(value: str) -> tuple[str | None, str | None]:
    ranges = TIME_RANGE_PATTERN.findall(value)
    if not ranges:
        return None, None
    starts = [_normalize_time(start) for start, _ in ranges]
    ends = [_normalize_time(end) for _, end in ranges]
    return " | ".join(starts), " | ".join(ends)


def _parse_course_page(html: str) -> tuple[bool, list[dict[str, str | None]]]:
    parser = _CourseScheduleParser()
    parser.feed(html)
    parser.close()

    if not parser.table_found:
        raise CoursePageParseError("course page did not contain the section table")

    sections: list[dict[str, str | None]] = []
    for row in parser.rows:
        if len(row) < 8 or not row[1].isdigit():
            continue
        time_start, time_end = _parse_time_range(row[4])
        sections.append(
            {
                "section_type": row[2] or None,
                "section": row[3] or None,
                "crn": row[1],
                "days": row[5] or None,
                "time_start": time_start,
                "time_end": time_end,
                "location": row[6] or None,
                "instructor": row[7] or None,
            }
        )

    course_exists = bool(parser.course_label.strip()) or bool(sections)
    return course_exists, sections


def _fetch_html(url: str) -> str:
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": "college-advisor-rebuild/1.0"},
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"upstream returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"upstream request failed: {exc}") from exc


def _course_url(course_code: str) -> str:
    subject, number = course_code.split(" ", maxsplit=1)
    return COURSE_URL_TEMPLATE.format(subject=subject, number=number)


@tool("get_course_sections", args_schema=GetCourseSectionsInput)
def get_course_sections(course_codes: list[str]) -> list[dict[str, Any]]:
    """Get current Spring 2026 section details for one to three UIUC courses."""
    results: list[dict[str, Any]] = []
    for course_code in course_codes:
        try:
            html = _fetch_html(_course_url(course_code))
            course_exists, sections = _parse_course_page(html)
        except (CoursePageParseError, RuntimeError) as exc:
            error_type = (
                "response_parse_failed"
                if isinstance(exc, CoursePageParseError)
                else "request_failed"
            )
            results.append(
                {
                    "course_code": course_code,
                    "sections": [],
                    "error": {
                        "type": error_type,
                        "message": str(exc),
                    },
                }
            )
            continue

        result: dict[str, Any] = {
            "course_code": course_code,
            "sections": sections,
        }
        if not course_exists:
            result["message"] = "no such course"
        results.append(result)
    return results


__all__ = ["GetCourseSectionsInput", "get_course_sections"]

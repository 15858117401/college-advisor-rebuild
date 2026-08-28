import argparse
import csv
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

from dotenv import load_dotenv

from embedding_client import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, embed_texts


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COURSES_CSV = PROJECT_ROOT / "Resource" / "stat_courses.csv"
INSTRUCTORS_CSV = PROJECT_ROOT / "Resource" / "stat_course_instructor_stats.csv"
EXPECTED_PROJECT_REF = "cyuonyibvzbwphzbgpta"
EXPECTED_COURSE_COUNT = 41
EXPECTED_INSTRUCTOR_COUNT = 117
COURSE_CODE_PATTERN = re.compile(r"^STAT (\d{3})$")

COURSE_HEADERS = [
    "course_code",
    "subject",
    "course_number",
    "course_name",
    "credits",
    "description",
    "prerequisites",
    "credit_restrictions",
    "gen_ed",
    "total_students",
    "total_sections",
    "overall_gpa",
]
INSTRUCTOR_HEADERS = [
    "course_code",
    "instructor_name",
    "instructor_avg_gpa",
    "gpa_delta_from_course",
]
MISSING_MARKERS = {"n/a", "null", "unknown", "-", "–"}


@dataclass(frozen=True)
class ResourceData:
    courses: list[dict[str, Any]]
    instructors: list[dict[str, Any]]

    @property
    def courses_without_gpa(self) -> int:
        return sum(course["overall_gpa"] is None for course in self.courses)


def _read_csv(path: Path, expected_headers: list[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != expected_headers:
            raise ValueError(
                f"{path.name} headers do not match the required order: {reader.fieldnames}"
            )
        rows = list(reader)
    for row_number, row in enumerate(rows, start=2):
        for field, value in row.items():
            if value.strip().lower() in MISSING_MARKERS:
                raise ValueError(
                    f"{path.name} row {row_number} field {field} uses a missing-value marker"
                )
    return rows


def _optional_text(value: str) -> str | None:
    normalized = " ".join(value.split())
    return normalized or None


def _required_text(value: str, *, field: str, row_number: int) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"row {row_number} has an empty {field}")
    return normalized


def _optional_int(value: str, *, field: str, row_number: int) -> int | None:
    if not value.strip():
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"row {row_number} has invalid {field}: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"row {row_number} has negative {field}")
    return parsed


def _optional_float(
    value: str,
    *,
    field: str,
    row_number: int,
    minimum: float,
    maximum: float,
) -> float | None:
    if not value.strip():
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"row {row_number} has invalid {field}: {value!r}") from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(
            f"row {row_number} has {field} outside {minimum}..{maximum}: {parsed}"
        )
    return parsed


def load_resource_data(
    courses_path: Path = COURSES_CSV,
    instructors_path: Path = INSTRUCTORS_CSV,
) -> ResourceData:
    raw_courses = _read_csv(courses_path, COURSE_HEADERS)
    raw_instructors = _read_csv(instructors_path, INSTRUCTOR_HEADERS)

    courses: list[dict[str, Any]] = []
    for row_number, row in enumerate(raw_courses, start=2):
        course_code = _required_text(
            row["course_code"], field="course_code", row_number=row_number
        )
        match = COURSE_CODE_PATTERN.fullmatch(course_code)
        if match is None:
            raise ValueError(f"row {row_number} has invalid course_code: {course_code!r}")
        if row["subject"] != "STAT" or row["course_number"] != match.group(1):
            raise ValueError(f"row {row_number} has inconsistent course identifiers")

        total_students = _optional_int(
            row["total_students"], field="total_students", row_number=row_number
        )
        total_sections = _optional_int(
            row["total_sections"], field="total_sections", row_number=row_number
        )
        overall_gpa = _optional_float(
            row["overall_gpa"],
            field="overall_gpa",
            row_number=row_number,
            minimum=0.0,
            maximum=4.0,
        )
        if len({value is None for value in (total_students, total_sections, overall_gpa)}) > 1:
            raise ValueError(
                f"row {row_number} must have all three course GPA summary fields or none"
            )

        courses.append(
            {
                "course_code": course_code,
                "subject": "STAT",
                "course_number": int(match.group(1)),
                "course_name": _required_text(
                    row["course_name"], field="course_name", row_number=row_number
                ),
                "credits": _required_text(
                    row["credits"], field="credits", row_number=row_number
                ),
                "description": _required_text(
                    row["description"], field="description", row_number=row_number
                ),
                "prerequisites": _optional_text(row["prerequisites"]),
                "credit_restrictions": _optional_text(row["credit_restrictions"]),
                "gen_ed": _optional_text(row["gen_ed"]),
                "total_students": total_students,
                "total_sections": total_sections,
                "overall_gpa": overall_gpa,
            }
        )

    course_codes = [course["course_code"] for course in courses]
    duplicate_courses = [
        code for code, count in Counter(course_codes).items() if count > 1
    ]
    if duplicate_courses:
        raise ValueError(f"duplicate course codes: {duplicate_courses}")

    instructors: list[dict[str, Any]] = []
    for row_number, row in enumerate(raw_instructors, start=2):
        course_code = _required_text(
            row["course_code"], field="course_code", row_number=row_number
        )
        instructor_name = _required_text(
            row["instructor_name"], field="instructor_name", row_number=row_number
        )
        if instructor_name.casefold() == "all sections":
            raise ValueError(f"row {row_number} contains All Sections as an instructor")
        instructors.append(
            {
                "course_code": course_code,
                "instructor_name": instructor_name,
                "instructor_avg_gpa": _optional_float(
                    row["instructor_avg_gpa"],
                    field="instructor_avg_gpa",
                    row_number=row_number,
                    minimum=0.0,
                    maximum=4.0,
                ),
                "gpa_delta_from_course": _optional_float(
                    row["gpa_delta_from_course"],
                    field="gpa_delta_from_course",
                    row_number=row_number,
                    minimum=-4.0,
                    maximum=4.0,
                ),
            }
        )

    orphan_codes = sorted(
        {row["course_code"] for row in instructors} - set(course_codes)
    )
    if orphan_codes:
        raise ValueError(f"instructor rows reference unknown courses: {orphan_codes}")
    instructor_keys = [
        (
            row["course_code"],
            row["instructor_name"],
            row["instructor_avg_gpa"],
            row["gpa_delta_from_course"],
        )
        for row in instructors
    ]
    if len(instructor_keys) != len(set(instructor_keys)):
        raise ValueError("instructor CSV contains completely duplicate rows")

    if len(courses) != EXPECTED_COURSE_COUNT:
        raise ValueError(
            f"expected {EXPECTED_COURSE_COUNT} courses, found {len(courses)}"
        )
    if len(instructors) != EXPECTED_INSTRUCTOR_COUNT:
        raise ValueError(
            f"expected {EXPECTED_INSTRUCTOR_COUNT} instructor rows, found {len(instructors)}"
        )
    return ResourceData(courses=courses, instructors=instructors)


def validation_summary(data: ResourceData) -> dict[str, Any]:
    stat_100 = next(
        course for course in data.courses if course["course_code"] == "STAT 100"
    )
    return {
        "courses": len(data.courses),
        "instructor_rows": len(data.instructors),
        "courses_without_gpa": data.courses_without_gpa,
        "stat_100": {
            "course_name": stat_100["course_name"],
            "total_students": stat_100["total_students"],
            "total_sections": stat_100["total_sections"],
            "overall_gpa": stat_100["overall_gpa"],
        },
    }


def validate_supabase_url(url: str) -> None:
    parsed = urlparse(url)
    expected_host = f"{EXPECTED_PROJECT_REF}.supabase.co"
    if parsed.scheme != "https" or parsed.hostname != expected_host:
        raise RuntimeError(
            f"SUPABASE_URL must target project {EXPECTED_PROJECT_REF} ({expected_host})"
        )


def create_supabase_client() -> Any:
    load_dotenv(PROJECT_ROOT / ".env")
    url = os.getenv("SUPABASE_URL")
    secret_key = os.getenv("SUPABASE_SECRET_KEY")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set")
    if not secret_key:
        raise RuntimeError("SUPABASE_SECRET_KEY is not set")
    validate_supabase_url(url)

    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("the supabase package is not installed") from exc
    return create_client(url, secret_key)


def upload_snapshot(
    data: ResourceData,
    vectors: Sequence[Sequence[float]],
    *,
    supabase_client: Any,
) -> dict[str, Any]:
    if len(vectors) != len(data.courses):
        raise ValueError("course and embedding counts do not match")

    course_rows: list[dict[str, Any]] = []
    for course, vector_values in zip(data.courses, vectors, strict=True):
        vector = [float(value) for value in vector_values]
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"{course['course_code']} embedding has {len(vector)} dimensions"
            )
        course_rows.append({**course, "embedding": vector})

    response = supabase_client.rpc(
        "replace_stat_resource_snapshot",
        {
            "course_rows": course_rows,
            "instructor_rows": data.instructors,
        },
    ).execute()
    result_rows = response.data or []
    if not result_rows:
        raise RuntimeError("Supabase import RPC returned no result")
    result = result_rows[0]
    if result.get("courses_upserted") != len(data.courses):
        raise RuntimeError(f"unexpected imported course count: {result}")
    if result.get("instructor_rows_inserted") != len(data.instructors):
        raise RuntimeError(f"unexpected imported instructor count: {result}")

    stat_100_index = next(
        index
        for index, course in enumerate(data.courses)
        if course["course_code"] == "STAT 100"
    )
    matches = supabase_client.rpc(
        "match_courses",
        {
            "query_embedding": list(vectors[stat_100_index]),
            "match_count": 3,
            "match_threshold": 0.0,
        },
    ).execute().data
    if not matches or matches[0].get("course_code") != "STAT 100":
        raise RuntimeError("semantic search did not rank STAT 100 first")
    return {
        "courses": result["courses_upserted"],
        "instructor_rows": result["instructor_rows_inserted"],
        "semantic_search_top_match": matches[0]["course_code"],
    }


def run_smoke(data: ResourceData) -> dict[str, Any]:
    stat_100 = next(
        course for course in data.courses if course["course_code"] == "STAT 100"
    )
    vector = embed_texts([stat_100["description"]])[0]
    return {
        "course_code": "STAT 100",
        "model": EMBEDDING_MODEL,
        "dimensions": len(vector),
        "status": "ok",
    }


def run_upload(data: ResourceData) -> dict[str, Any]:
    vectors = embed_texts([course["description"] for course in data.courses])
    result = upload_snapshot(
        data,
        vectors,
        supabase_client=create_supabase_client(),
    )
    return {
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIMENSIONS,
        **result,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate, embed, and import the UIUC STAT resource CSVs."
    )
    parser.add_argument("command", choices=("validate", "smoke", "upload"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = load_resource_data()
    if args.command == "validate":
        result = validation_summary(data)
    elif args.command == "smoke":
        result = run_smoke(data)
    else:
        result = run_upload(data)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

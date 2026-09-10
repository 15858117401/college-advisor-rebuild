"""Read and resolve the stored program metadata without a hard-coded major catalog."""
import re
from typing import Any

from Supabase.resource_queries import fetch_all_rows


TABLE_NAME = "graduation_requirement_documents"
CATALOG_YEAR = "2026-2027"
PROGRAM_FIELDS = (
    "document_key,program_code,program_name,degree_code,document_type,catalog_year,source_url"
)
LEGACY_KEYS = {
    "math": "UIUC-MATH-BSLAS-2026-2027",
    "stats": "UIUC-STAT-BSLAS-2026-2027",
}


def normalize_program(value: str) -> str:
    value = value.casefold().replace("&", " and ").replace("+", " and ")
    return " ".join(re.findall(r"\w+", value))


def load_programs(client: Any) -> list[dict]:
    return fetch_all_rows(lambda: (
        client.table(TABLE_NAME).select(PROGRAM_FIELDS)
        .eq("catalog_year", CATALOG_YEAR).order("document_key")
    ))


def exact_program_matches(query: str, programs: list[dict]) -> list[dict]:
    normalized = normalize_program(query)
    normalized = normalize_program(LEGACY_KEYS.get(normalized, query))
    return [
        program for program in programs
        if normalized in {
            normalize_program(program[field] or "")
            for field in ("document_key", "program_code", "program_name")
        } | {normalize_program(program["program_name"].split(",", 1)[0])}
    ]


def program_candidates(query: str, programs: list[dict]) -> list[dict]:
    normalized = normalize_program(query)
    if normalized in LEGACY_KEYS:
        return exact_program_matches(query, programs)
    words = set(normalized.split())
    return [
        program for program in programs
        if words and words <= set(normalize_program(" ".join(
            str(program.get(field) or "")
            for field in ("program_name", "program_code", "document_key")
        )).split())
    ]

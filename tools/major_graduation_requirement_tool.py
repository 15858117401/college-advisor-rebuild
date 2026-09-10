import json

from langchain_core.tools import ToolException, tool
from pydantic import BaseModel, ConfigDict, Field, field_validator

from Supabase.degree_programs import (
    LEGACY_KEYS, TABLE_NAME, exact_program_matches, load_programs, program_candidates,
)
from Supabase.import_stat_resources import create_supabase_client


MAJOR_DOCUMENT_KEYS = LEGACY_KEYS


class MajorGraduationRequirementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    major: str = Field(
        min_length=1,
        description=(
            "Exact stored program name, program code, or document_key from "
            "find_degree_programs. Legacy aliases 'math' and 'stats' also work."
        ),
    )

    @field_validator("major")
    @classmethod
    def nonblank_major(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("major cannot be blank")
        return value.strip()


@tool("major_graduation_requirement", args_schema=MajorGraduationRequirementInput)
def major_graduation_requirement(major: str) -> str:
    """Get the exact stored 2026-2027 UIUC major requirement Markdown.

    Supports all stored programs; use find_degree_programs to discover names
    and keys. Ambiguous or unavailable names require a more specific choice.
    A general-major document does not verify a concentration's requirements.
    Biology returns its stored redirect, not another program's requirements.
    This tool does not return LAS general education requirements.
    """
    client = create_supabase_client()
    programs = load_programs(client)
    matches = exact_program_matches(major, programs)
    if len(matches) != 1:
        candidates = matches or program_candidates(major, programs)
        raise ToolException(json.dumps({
            "error": "ambiguous_program" if len(matches) > 1 or len(candidates) > 1 else "program_not_found",
            "message": (
                "No unique exact stored program matches the request. Choose the intended "
                "program by document_key from these candidates or use find_degree_programs. "
                "Do not substitute a different major or general-major rules for missing "
                "concentration requirements. Ask for clarification if the choice is unclear."
            ),
            "requested_program": major,
            "candidates": candidates,
        }, ensure_ascii=False))
    document_key = matches[0]["document_key"]
    rows = client.table(TABLE_NAME).select("content_markdown").eq(
        "document_key", document_key
    ).execute().data or []
    content = rows[0].get("content_markdown") if len(rows) == 1 else None
    if not isinstance(content, str) or not content.strip():
        raise ToolException(f"No stored requirement Markdown is available for {document_key}.")
    return content


__all__ = ["MajorGraduationRequirementInput", "major_graduation_requirement"]

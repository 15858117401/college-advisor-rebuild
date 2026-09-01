from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from Supabase.import_stat_resources import create_supabase_client


Major = Literal["math", "stats"]

MAJOR_DOCUMENT_KEYS: dict[Major, str] = {
    "math": "UIUC-MATH-BSLAS-2026-2027",
    "stats": "UIUC-STAT-BSLAS-2026-2027",
}
TABLE_NAME = "graduation_requirement_documents"


class GetGraduationRequirementsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    major: Major = Field(
        description=(
            "The UIUC BSLAS major whose 2026-2027 graduation requirements "
            "should be retrieved: 'math' or 'stats'."
        )
    )


@tool("get_graduation_requirements", args_schema=GetGraduationRequirementsInput)
def get_graduation_requirements(major: Major) -> str:
    """Get the major graduation requirements for Math or Statistics.

    Returns the stored 2026-2027 Catalog Markdown without interpreting it as
    degree-audit rules or creating a personalized degree plan.
    """
    major_document_key = MAJOR_DOCUMENT_KEYS[major]
    response = (
        create_supabase_client()
        .table(TABLE_NAME)
        .select("content_markdown")
        .eq("document_key", major_document_key)
        .execute()
    )

    rows = response.data or []
    content = rows[0].get("content_markdown") if len(rows) == 1 else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(
            f"missing graduation requirement Markdown for {major_document_key}"
        )

    return content


__all__ = ["GetGraduationRequirementsInput", "get_graduation_requirements"]

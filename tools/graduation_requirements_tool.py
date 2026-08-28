from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from Supabase.import_stat_resources import create_supabase_client


Major = Literal["math", "stats"]

LAS_DOCUMENT_KEY = "UIUC-LAS-BSLAS-2026-2027"
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
    """Get the LAS and major graduation requirements for Math or Statistics.

    Returns the stored 2026-2027 Catalog Markdown without interpreting it as
    degree-audit rules or creating a personalized degree plan.
    """
    major_document_key = MAJOR_DOCUMENT_KEYS[major]
    document_keys = [LAS_DOCUMENT_KEY, major_document_key]
    response = (
        create_supabase_client()
        .table(TABLE_NAME)
        .select("document_key,content_markdown")
        .in_("document_key", document_keys)
        .execute()
    )

    content_by_key = {
        row["document_key"]: row.get("content_markdown")
        for row in (response.data or [])
        if row.get("document_key") in document_keys
    }
    for document_key in document_keys:
        content = content_by_key.get(document_key)
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"missing graduation requirement Markdown for {document_key}"
            )

    return (
        "# LAS COMMON REQUIREMENTS\n\n"
        f"{content_by_key[LAS_DOCUMENT_KEY]}"
        "\n\n# MAJOR REQUIREMENTS\n\n"
        f"{content_by_key[major_document_key]}"
    )


__all__ = ["GetGraduationRequirementsInput", "get_graduation_requirements"]

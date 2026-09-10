from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from Supabase.degree_programs import load_programs, program_candidates
from Supabase.import_stat_resources import create_supabase_client


class FindDegreeProgramsInput(BaseModel):
    query: str = Field(min_length=1, description="Program name or keywords, e.g. Economics, Mathematics, or Biology.")

    @field_validator("query")
    @classmethod
    def nonblank_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query cannot be blank")
        return value.strip()


@tool("find_degree_programs", args_schema=FindDegreeProgramsInput)
def find_degree_programs(query: str) -> list[dict]:
    """Discover stored UIUC 2026-2027 programs and their exact document keys.

    Returns matching program names, codes, degree codes, document types, years,
    and source URLs. Related programs are separate choices, not interchangeable
    requirements. An empty list means no matching stored program was found.
    Search the base major separately if concentration metadata is unavailable.
    """
    return program_candidates(query, load_programs(create_supabase_client()))


__all__ = ["FindDegreeProgramsInput", "find_degree_programs"]

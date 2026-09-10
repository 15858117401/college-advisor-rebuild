from pathlib import Path

from langgraph.runtime import Runtime

from react_agent import build_react_agent
from state import (
    AdvisorContext,
    AdvisorState,
    messages_with_current_input,
    profile_from_runtime,
)
from tools.course_details_tool import get_course_details
from tools.degree_programs_tool import find_degree_programs
from tools.general_education_graduation_requirement_tool import (
    general_education_graduation_requirement,
)
from tools.major_graduation_requirement_tool import major_graduation_requirement
from tools.course_instructor_gpa_tool import get_course_instructor_gpas
from tools.course_search_tool import find_courses
from tools.course_sections_tool import get_course_sections
from tools.professor_research_tools import (
    search_rate_my_professor,
    search_reddit,
)


CATALOG_SYSTEM_PROMPT = (
    Path(__file__).resolve().parents[1]
    / "prompt"
    / "catalog_lookup_prompt.txt"
).read_text(encoding="utf-8")

CATALOG_SKILLS: list[str] = []
CATALOG_TOOLS = [
    get_course_details,
    major_graduation_requirement,
    general_education_graduation_requirement,
    find_degree_programs,
    get_course_instructor_gpas,
    find_courses,
    get_course_sections,
    search_rate_my_professor,
    search_reddit,
]

catalog_agent = build_react_agent(
    CATALOG_SYSTEM_PROMPT,
    tools=CATALOG_TOOLS,
    skills=CATALOG_SKILLS,
)


def catalog_lookup(
    state: AdvisorState,
    runtime: Runtime[AdvisorContext] | None = None,
) -> dict:
    """Run the catalog ReAct agent with past messages and current input."""
    profile = profile_from_runtime(runtime)
    result = catalog_agent.invoke(
        {"messages": messages_with_current_input(state, profile=profile)},
        config={"recursion_limit": 12},
    )
    return {"response": result["messages"][-1].content}


__all__ = [
    "CATALOG_SKILLS",
    "CATALOG_SYSTEM_PROMPT",
    "CATALOG_TOOLS",
    "catalog_agent",
    "catalog_lookup",
]

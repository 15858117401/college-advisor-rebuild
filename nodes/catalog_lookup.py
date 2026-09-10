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
from tools.graduation_requirements_tool import get_graduation_requirements
from tools.course_instructor_gpa_tool import get_course_instructor_gpas
from tools.course_search_tool import find_courses
from tools.course_sections_tool import get_course_sections
from tools.professor_research_tools import (
    search_rate_my_professor,
    search_reddit,
)


CATALOG_SYSTEM_PROMPT = """You are a factual course catalog lookup agent.

Use the available tools to answer questions about courses, course sections,
historical instructor GPA statistics, graduation requirements, and public
student reviews of UIUC professors.
Base answers on tool results and do not invent missing information.
Instructor GPA statistics are not tied to specific sections or academic terms.
Always use get_graduation_requirements for the requested program's graduation
requirements and preserve the returned requirement Markdown. Use find_degree_programs
to discover exact names and keys when needed. Related majors are not interchangeable.
All stored majors and course subjects are supported; do not restrict lookups to STAT.
Do not present general-major rules as verified concentration-specific requirements.
The current request or stated scenario takes precedence over conflicting profile context.
For a different hypothetical student, do not import personal facts from the saved profile.
Only Spring 2026 section information is available; future offerings are unknown.
When you have enough information, answer the user directly without calling more tools.
Do not create personalized course or degree plans.


"""

CATALOG_SKILLS: list[str] = []
CATALOG_TOOLS = [
    get_course_details,
    get_graduation_requirements,
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

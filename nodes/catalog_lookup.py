from state import AdvisorState, messages_with_current_input
from react_agent import build_react_agent
from skills import load_skill
from tools.course_details_tool import get_course_details
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
Always use get_graduation_requirements for Math or Statistics graduation
requirements and preserve the returned requirement Markdown.
When you have enough information, answer the user directly without calling more tools.
Do not create personalized course or degree plans.


"""

CATALOG_SKILLS: list[str] = [load_skill("professor_research")]
CATALOG_TOOLS = [
    get_course_details,
    get_graduation_requirements,
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


def catalog_lookup(state: AdvisorState) -> dict:
    """Run the catalog ReAct agent with past messages and current input."""
    result = catalog_agent.invoke(
        {"messages": messages_with_current_input(state)},
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

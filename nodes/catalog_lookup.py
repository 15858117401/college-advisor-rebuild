from state import AdvisorState
from react_agent import build_react_agent
from tools.course_details_tool import get_course_details
from tools.graduation_requirements_tool import get_graduation_requirements
from tools.course_instructor_gpa_tool import get_course_instructor_gpas
from tools.course_search_tool import find_courses
from tools.course_sections_tool import get_course_sections


CATALOG_SYSTEM_PROMPT = """You are a factual course catalog lookup agent.

Use the available tools to answer questions about courses, course sections,
historical instructor GPA statistics, and graduation requirements.
Base answers on tool results and do not invent missing information.
Instructor GPA statistics are not tied to specific sections or academic terms.
Always use get_graduation_requirements for Math or Statistics graduation
requirements and preserve the returned requirement Markdown.
When you have enough information, answer the user directly without calling more tools.
Do not create personalized course or degree plans.
"""

CATALOG_TOOLS = [
    get_course_details,
    get_graduation_requirements,
    get_course_instructor_gpas,
    find_courses,
    get_course_sections,
]

catalog_agent = build_react_agent(
    CATALOG_SYSTEM_PROMPT,
    tools=CATALOG_TOOLS,
)


def catalog_lookup(state: AdvisorState) -> dict:
    """Run the catalog ReAct agent with the complete conversation."""
    result = catalog_agent.invoke(
        {"messages": state["messages"]},
        config={"recursion_limit": 12},
    )
    return {"response": result["messages"][-1].content}


__all__ = [
    "CATALOG_SYSTEM_PROMPT",
    "CATALOG_TOOLS",
    "catalog_agent",
    "catalog_lookup",
]

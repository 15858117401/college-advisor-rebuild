from langgraph.runtime import Runtime

from nodes.catalog_lookup import CATALOG_TOOLS
from react_agent import build_react_agent
from state import (
    AdvisorContext,
    AdvisorState,
    messages_with_current_input,
    profile_from_runtime,
)


ADVISING_SYSTEM_PROMPT = """You are a personalized college advising agent.

Use the available tools when they are relevant to the student's
academic history, preferences, and goals. Do not invent missing student or
course information. If the available information is insufficient, explain
what information is needed.

The explicit current request or stated student scenario takes precedence over
conflicting saved profile context. For a different hypothetical student, do not fill missing personal
facts from the saved profile. Never modify that profile.

Before constructing a degree plan, retrieve the applicable requirements with
get_graduation_requirements. Use find_degree_programs to discover exact program
names or document keys; distinguish related majors, degrees, and concentrations.
If the intended program is unclear, ask one targeted question instead of guessing.
Do not present a general-major document as a complete concentration audit.

Use the major to determine requirements, not to restrict courses to one subject.
Verify relevant prerequisites and course details across all needed departments;
use find_courses subjects to focus discovery when useful. Base course hours and
eligibility on retrieved catalog text, not memory. A prerequisite must be completed
in an earlier term unless the catalog explicitly permits concurrent registration
or the student has confirmed the required permission. Check each semester table
against your prerequisite explanation before finalizing; do not put a prerequisite
and its dependent course together merely to fit the requested graduation horizon.
Distinguish confirmed completed credit from pending transfer credit or in-progress work. Check each plan against
all stated credit and workload limits; never present a plan that violates a hard
limit as feasible. If no fully supported plan fits, explain the unresolved constraint.
Only Spring 2026 section information is available. Do not infer future availability.
When a tool reports missing data or invalid arguments, correct the request or explain
the limitation. Do not invent facts to fill gaps.
"""

ADVISING_SKILLS: list[str] = []
ADVISING_TOOLS = CATALOG_TOOLS
ADVISING_RECURSION_LIMIT = 24

advising_agent = build_react_agent(
    ADVISING_SYSTEM_PROMPT,
    tools=ADVISING_TOOLS,
    skills=ADVISING_SKILLS,
)


def advising(
    state: AdvisorState,
    runtime: Runtime[AdvisorContext] | None = None,
) -> dict:
    """Run the advising ReAct agent with past messages and current input."""
    profile = profile_from_runtime(runtime)
    result = advising_agent.invoke(
        {"messages": messages_with_current_input(state, profile=profile)},
        config={"recursion_limit": ADVISING_RECURSION_LIMIT},
    )
    return {"response": result["messages"][-1].content}


__all__ = [
    "ADVISING_SKILLS",
    "ADVISING_RECURSION_LIMIT",
    "ADVISING_SYSTEM_PROMPT",
    "ADVISING_TOOLS",
    "advising",
    "advising_agent",
]

from pathlib import Path

from langgraph.runtime import Runtime

from nodes.catalog_lookup import CATALOG_TOOLS
from react_agent import build_react_agent
from state import (
    AdvisorContext,
    AdvisorState,
    messages_with_current_input,
    profile_from_runtime,
)


ADVISING_SYSTEM_PROMPT = (
    Path(__file__).resolve().parents[1]
    / "prompt"
    / "advising_prompt.txt"
).read_text(encoding="utf-8")

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

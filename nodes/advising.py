import logging
from pathlib import Path
from time import perf_counter

from langgraph.runtime import Runtime

from nodes.catalog_lookup import CATALOG_TOOLS
from react_agent import build_react_agent
from state import (
    AdvisorContext,
    AdvisorState,
    messages_with_current_input,
    profile_from_runtime,
)
from tools.skill_loader_tool import SKILL_DESCRIPTIONS, load_skill


logger = logging.getLogger(f"college_advisor.{__name__}")

_ADVISING_BASE_PROMPT = (
    Path(__file__).resolve().parents[1]
    / "prompt"
    / "advising_prompt.txt"
).read_text(encoding="utf-8")
_SKILL_INDEX = "\n".join(
    f"- `{name}`: {description}"
    for name, description in SKILL_DESCRIPTIONS.items()
)
ADVISING_SYSTEM_PROMPT = (
    f"{_ADVISING_BASE_PROMPT.rstrip()}\n\n"
    f"## Available Advising Skills\n\n{_SKILL_INDEX}\n\n"
    "When a request matches a skill description, call `load_skill` with its "
    "exact name before following that skill's instructions."
)

ADVISING_TOOLS = [*CATALOG_TOOLS, load_skill]
ADVISING_RECURSION_LIMIT = 24

advising_agent = build_react_agent(
    ADVISING_SYSTEM_PROMPT,
    tools=ADVISING_TOOLS,
)


def advising(
    state: AdvisorState,
    runtime: Runtime[AdvisorContext] | None = None,
) -> dict:
    """Run the advising ReAct agent with past messages and current input."""
    started = perf_counter()
    logger.info("Advising 开始")
    profile = profile_from_runtime(runtime)
    result = advising_agent.invoke(
        {"messages": messages_with_current_input(state, profile=profile)},
        config={"recursion_limit": ADVISING_RECURSION_LIMIT},
    )
    response = result["messages"][-1].content
    logger.info("Advising 完成，耗时 %.2fs", perf_counter() - started)
    return {"response": response}


__all__ = [
    "ADVISING_RECURSION_LIMIT",
    "ADVISING_SYSTEM_PROMPT",
    "ADVISING_TOOLS",
    "advising",
    "advising_agent",
]

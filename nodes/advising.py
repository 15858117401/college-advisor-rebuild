from langchain_core.tools import BaseTool

from react_agent import build_react_agent
from skills import load_skill
from state import AdvisorState, messages_with_current_input
from tools.professor_research_tools import (
    search_rate_my_professor,
    search_reddit,
)


ADVISING_SYSTEM_PROMPT = """You are a personalized college advising agent.

Use the supplied skills and tools when they are relevant to the student's
academic history, preferences, and goals. Do not invent missing student or
course information. If the available information is insufficient, explain
what information is needed.
"""

ADVISING_SKILLS: list[str] = [load_skill("professor_research")]
ADVISING_TOOLS: list[BaseTool] = [
    search_rate_my_professor,
    search_reddit,
]

advising_agent = build_react_agent(
    ADVISING_SYSTEM_PROMPT,
    tools=ADVISING_TOOLS,
    skills=ADVISING_SKILLS,
)


def advising(state: AdvisorState) -> dict:
    """Run the advising ReAct agent with past messages and current input."""
    result = advising_agent.invoke(
        {"messages": messages_with_current_input(state)},
        config={"recursion_limit": 12},
    )
    return {"response": result["messages"][-1].content}


__all__ = [
    "ADVISING_SKILLS",
    "ADVISING_SYSTEM_PROMPT",
    "ADVISING_TOOLS",
    "advising",
    "advising_agent",
]

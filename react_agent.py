from collections.abc import Sequence

from langchain.agents import create_agent
from langchain_core.tools import BaseTool

from client.llm_client import llm_client


def _with_skills(system_prompt: str, skills: Sequence[str]) -> str:
    """Append caller-provided skill instructions to an agent prompt."""
    skill_sections = [skill.strip() for skill in skills if skill.strip()]
    if not skill_sections:
        return system_prompt
    return f"{system_prompt.rstrip()}\n\n# Skills\n\n" + "\n\n---\n\n".join(
        skill_sections
    )


def build_react_agent(
    system_prompt: str,
    tools: Sequence[BaseTool] = (),
    *,
    skills: Sequence[str] = (),
):
    """Build a ReAct agent with independent skill instructions and tools."""
    return create_agent(
        model=llm_client,
        tools=list(tools),
        system_prompt=_with_skills(system_prompt, skills),
    )


__all__ = ["build_react_agent"]

from collections.abc import Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, ToolException
from pydantic import ValidationError

from client.llm_client import llm_client


@wrap_tool_call
def handle_expected_tool_errors(request, handler):
    """Let the agent repair expected input/resource errors; propagate other failures."""
    try:
        return handler(request)
    except (ValidationError, ToolException) as exc:
        return ToolMessage(
            content=f"Tool request could not be completed: {exc}",
            tool_call_id=request.tool_call["id"],
            status="error",
        )


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
        middleware=[handle_expected_tool_errors],
        system_prompt=_with_skills(system_prompt, skills),
    )


__all__ = ["build_react_agent"]

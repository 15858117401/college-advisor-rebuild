from collections.abc import Sequence

from langchain.agents import create_agent
from langchain_core.tools import BaseTool

from client.llm_client import llm_client


def build_react_agent(system_prompt: str, tools: Sequence[BaseTool]):
    """Build a ReAct agent with a caller-provided tool group."""
    return create_agent(
        model=llm_client,
        tools=list(tools),
        system_prompt=system_prompt,
    )


__all__ = ["build_react_agent"]

import logging
from collections.abc import Sequence
from time import perf_counter

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, ToolException
from pydantic import ValidationError

from client.llm_client import llm_client


logger = logging.getLogger(f"college_advisor.{__name__}")


@wrap_tool_call
def handle_expected_tool_errors(request, handler):
    """Let the agent repair expected input/resource errors; propagate other failures."""
    tool_name = request.tool_call["name"]
    started = perf_counter()
    logger.info("工具 %s 开始", tool_name)
    try:
        result = handler(request)
    except (ValidationError, ToolException) as exc:
        result = ToolMessage(
            content=f"Tool request could not be completed: {exc}",
            tool_call_id=request.tool_call["id"],
            status="error",
        )
    except Exception:
        logger.error("工具 %s 异常，耗时 %.2fs", tool_name, perf_counter() - started)
        raise

    if isinstance(result, ToolMessage) and result.status == "error":
        logger.warning("工具 %s 失败，耗时 %.2fs", tool_name, perf_counter() - started)
    else:
        logger.info("工具 %s 完成，耗时 %.2fs", tool_name, perf_counter() - started)
    return result


def build_react_agent(
    system_prompt: str,
    tools: Sequence[BaseTool] = (),
):
    """Build a ReAct agent with shared tool-error handling."""
    return create_agent(
        model=llm_client,
        tools=list(tools),
        middleware=[handle_expected_tool_errors],
        system_prompt=system_prompt,
    )


__all__ = ["build_react_agent"]

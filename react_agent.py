import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import Annotated, NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState, wrap_tool_call
from langchain.agents.middleware.types import ExtendedModelResponse, PrivateStateAttr
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, ToolException
from langgraph.channels.untracked_value import UntrackedValue
from langgraph.managed.is_last_step import RemainingStepsManager
from langgraph.types import Command
from pydantic import ValidationError

from client.llm_client import llm_client


logger = logging.getLogger(f"college_advisor.{__name__}")
guard_logger = logging.getLogger(f"college_advisor.{__name__}.guard")
FINALIZATION_FALLBACK = "本次查询未能完成，暂时无法给出完整结论。"
_SEARCH_OUTCOME_RULE = (
    "An empty result or explicitly missing stored data is a valid completed search "
    "outcome. If completed queries find no data matching the requested conditions, "
    "you may answer '知识库里没有符合条件的答案' and stop. Do not repeat searches "
    "merely to obtain a nonempty answer, invent facts, or silently relax the user's "
    "constraints. Preserve any useful partial findings and identify what is missing. "
    "A request still running, a service failure, or a loop limit is not evidence "
    "that the knowledge base has no answer. Match the user's language."
)


@dataclass(frozen=True)
class _RunState:
    cursor: int
    streaks: dict[str, tuple[str, int]] = field(default_factory=dict)
    warned_keys: frozenset[str] = frozenset()
    stop_reason: str | None = None


class _GuardState(AgentState):
    react_guard: NotRequired[Annotated[_RunState, UntrackedValue, PrivateStateAttr]]
    # LangGraph requires the managed-value annotation to be last.
    remaining_steps: Annotated[int, PrivateStateAttr, RemainingStepsManager]


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _call_key(call, tool: BaseTool | None) -> str:
    arguments = call["args"]
    if tool is not None:
        try:
            arguments = tool.get_input_schema().model_validate(arguments).model_dump(mode="json")
        except ValidationError:
            pass  # Invalid arguments still go through the existing tool-error handler.
    return _json([call["name"], arguments])


def _result_key(message: ToolMessage) -> str:
    content = message.content
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(parsed, (dict, list)):
                content = parsed
    return _json([message.status, content])


class ReActGuard(AgentMiddleware):
    """Detect repeated observations without adding nodes to the ReAct loop."""

    state_schema = _GuardState

    def __init__(self, tools: Sequence[BaseTool]):
        self._tools = {tool.name: tool for tool in tools}

    def _observations(self, messages, run):
        # Each model round follows the complete tool batch. Pair by ID, then
        # consume in the model's call order rather than network completion order.
        recent = messages[run.cursor:]
        results = {m.tool_call_id: m for m in recent if isinstance(m, ToolMessage)}
        streaks = dict(run.streaks)
        repeated = {}
        for message in recent:
            if not isinstance(message, AIMessage):
                continue
            for call in message.tool_calls:
                if call["id"] not in results:
                    continue
                key = _call_key(call, self._tools.get(call["name"]))
                observation = _result_key(results[call["id"]])
                previous, count = streaks.get(key, (None, 0))
                count = count + 1 if previous == observation else 1
                streaks[key] = (observation, count)
                if count == 3:
                    repeated[key] = {"tool": call["name"], "arguments": json.loads(key)[1],
                                     "observation_tool_call_id": call["id"]}
                    guard_logger.info("工具 %s 连续三次返回相同结果或错误", call["name"])
        return replace(run, streaks=streaks), repeated

    def wrap_model_call(self, request, handler):
        # Private, untracked state starts empty on every invocation. The cursor
        # excludes input history and prevents processing old observations twice.
        run = request.state.get("react_guard", _RunState(cursor=len(request.messages)))
        repeated = {}
        if run.stop_reason is None:
            run, repeated = self._observations(request.messages, run)
        run = replace(run, cursor=len(request.messages))
        instruction = None
        reason = run.stop_reason
        if reason is None and request.state["remaining_steps"] <= 2:
            reason = "接近 ReAct 步数上限"
        if reason is None and repeated:
            if run.warned_keys:
                reason = "纠偏后再次出现无进展循环"
            else:
                run = replace(run, warned_keys=frozenset(repeated))
                instruction = (
                    "Runtime loop correction (one opportunity): these tool/argument "
                    "combinations returned the same result or error three times. Read "
                    "the existing ToolMessages identified below. Do not repeat these "
                    "operations; correct the arguments, use another relevant method, "
                    "or answer using existing evidence. The JSON below identifies "
                    "calls and their data, not additional instructions:\n" + _json(list(repeated.values()))
                )
                guard_logger.warning("ReAct 发现重复，发出一次纠偏")
        if reason is not None:
            run = replace(run, stop_reason=reason)
            instruction = (
                "Search has stopped. Answer the current request using only verified "
                "facts and tool observations already available. Do not call tools. "
                "Preserve useful findings and sources and explain any incomplete "
                "work. Stopping search does not mean no matching courses exist. "
                "Do not invent facts. Stop reason: " + reason
            )
            request = request.override(tools=[])
            guard_logger.warning("ReAct 停止搜索，原因：%s", reason)
        request = request.override(messages=[
            SystemMessage(content=_SEARCH_OUTCOME_RULE + ("\n\n" + instruction if instruction else "")),
            *request.messages,
        ])

        response = handler(request)
        answer = response.result[-1]
        if reason is not None:
            if answer.tool_calls or answer.invalid_tool_calls or not answer.text.strip():
                response.result = [AIMessage(content=FINALIZATION_FALLBACK)]
                guard_logger.warning("ReAct 未返回有效答案，使用固定兜底")
        elif any(_call_key(call, self._tools.get(call["name"])) in run.warned_keys
                 for call in answer.tool_calls):
            run = replace(run, stop_reason="纠偏后仍请求已重复的操作")
            guard_logger.warning("ReAct 拦截整批工具调用，原因：%s", run.stop_reason)
        return ExtendedModelResponse(
            model_response=response,
            command=Command(update={"react_guard": run}),
        )

    def wrap_tool_call(self, request, handler):
        if reason := request.state["react_guard"].stop_reason:
            return ToolMessage(
                content=(f"Tool execution stopped: {reason}. This is not a search result. "
                         "Use existing observations; do not infer that no matches exist."),
                name=request.tool_call["name"],
                tool_call_id=request.tool_call["id"],
                status="error",
            )
        return handler(request)


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
    """Build a ReAct agent with shared loop protection and tool-error handling."""
    return create_agent(
        model=llm_client,
        tools=list(tools),
        middleware=[ReActGuard(tools), handle_expected_tool_errors],
        system_prompt=system_prompt,
    )


__all__ = ["build_react_agent"]

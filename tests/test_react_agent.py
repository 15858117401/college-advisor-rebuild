import logging
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from react_agent import (
    FINALIZATION_FALLBACK, ReActGuard, build_react_agent, handle_expected_tool_errors,
)
import pytest
from langchain.tools import ToolRuntime
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool, ToolException
from pydantic import Field
from tools.course_details_tool import GetCourseDetailsInput


class BuildReactAgentTest(unittest.TestCase):
    @patch("react_agent.create_agent")
    def test_registers_tools_without_changing_prompt(
        self,
        create_agent,
    ) -> None:
        tools = [SimpleNamespace(name="first"), SimpleNamespace(name="second")]

        build_react_agent(
            "Base instructions.",
            tools=tools,
        )

        call = create_agent.call_args.kwargs
        self.assertEqual(call["tools"], tools)
        self.assertIsInstance(call["middleware"][0], ReActGuard)
        self.assertEqual(call["middleware"][1:], [handle_expected_tool_errors])
        create_agent.return_value.with_config.assert_not_called()
        self.assertEqual(call["system_prompt"], "Base instructions.")

    @patch("react_agent.create_agent")
    def test_tools_are_optional(self, create_agent) -> None:
        build_react_agent("Base instructions.")

        call = create_agent.call_args.kwargs
        self.assertEqual(call["tools"], [])
        self.assertIsInstance(call["middleware"][0], ReActGuard)
        self.assertEqual(call["middleware"][1:], [handle_expected_tool_errors])
        self.assertEqual(call["system_prompt"], "Base instructions.")




# Exercise the real agent/tool loop without network calls.


class ScriptedToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.mark.parametrize('invalid_code', ['MATH-416', 'MATH 999'])
def test_agent_recovers_from_validation_and_unsupported_resource(invalid_code, caplog):
    caplog.set_level(logging.INFO, logger="college_advisor")
    calls = []

    @tool(args_schema=GetCourseDetailsInput)
    def lookup(course_codes: list[str]) -> str:
        """Look up a course."""
        calls.append(course_codes)
        if course_codes == ['MATH 999']:
            raise ToolException('No stored resource. Try a supported course.')
        return 'Abstract Linear Algebra'

    model = ScriptedToolModel(responses=[
        AIMessage(content='', tool_calls=[{'name': 'lookup', 'args': {'course_codes': [invalid_code]}, 'id': 'bad'}]),
        AIMessage(content='', tool_calls=[{'name': 'lookup', 'args': {'course_codes': ['MATH416']}, 'id': 'good'}]),
        AIMessage(content='Abstract Linear Algebra'),
    ])
    with patch('react_agent.llm_client', model):
        agent = build_react_agent('Repair invalid requests.', tools=[lookup])
    result = agent.invoke({'messages': [('human', 'Find MATH 416.')]})
    messages = [message for message in result['messages'] if isinstance(message, ToolMessage)]
    assert messages[0].status == 'error'
    assert messages[0].tool_call_id == 'bad'
    assert messages[1].status == 'success'
    assert calls[-1] == ['MATH 416']
    assert result['messages'][-1].content == 'Abstract Linear Algebra'
    records = [r for r in caplog.records if r.name == 'college_advisor.react_agent']
    assert [r.levelno for r in records] == [
        logging.INFO, logging.WARNING, logging.INFO, logging.INFO,
    ]
    assert 'lookup 失败' in records[1].getMessage()
    assert 'lookup 完成' in records[-1].getMessage()
    assert 'Abstract Linear Algebra' not in caplog.text
    assert invalid_code not in caplog.text


def test_returned_tool_error_is_logged_as_failure(caplog):
    caplog.set_level(logging.INFO, logger="college_advisor")

    @tool
    def report_error() -> ToolMessage:
        """Return a recoverable tool error."""
        return ToolMessage(
            content="Private error details",
            tool_call_id="reported-error",
            status="error",
        )

    model = ScriptedToolModel(responses=[
        AIMessage(content='', tool_calls=[
            {'name': 'report_error', 'args': {}, 'id': 'reported-error'},
        ]),
        AIMessage(content='The resource is unavailable.'),
    ])
    with patch('react_agent.llm_client', model):
        agent = build_react_agent('Call the tool.', tools=[report_error])
    result = agent.invoke({'messages': [('human', 'Call the tool.')]})

    assert result['messages'][-1].content == 'The resource is unavailable.'
    records = [r for r in caplog.records if r.name == 'college_advisor.react_agent']
    assert [r.levelno for r in records] == [logging.INFO, logging.WARNING]
    assert 'report_error 失败' in records[-1].getMessage()
    assert 'Private error details' not in caplog.text


@pytest.mark.parametrize('error', [RuntimeError('service unavailable'), ValueError('programming failure')])
def test_unexpected_tool_failures_propagate(error, caplog):
    caplog.set_level(logging.INFO, logger="college_advisor")
    @tool
    def broken() -> str:
        """Exercise an unexpected failure."""
        raise error

    model = ScriptedToolModel(responses=[AIMessage(content='', tool_calls=[{'name': 'broken', 'args': {}, 'id': 'broken'}])])
    with patch('react_agent.llm_client', model):
        agent = build_react_agent('Call the tool.', tools=[broken])
    with pytest.raises(type(error), match=str(error)) as raised:
        agent.invoke({'messages': [('human', 'Call the tool.')]})
    assert raised.value is error
    records = [r for r in caplog.records if r.name == 'college_advisor.react_agent']
    assert [r.levelno for r in records] == [logging.INFO, logging.ERROR]
    assert 'broken 异常' in records[-1].getMessage()
    assert not any(r.exc_info for r in records)


class RecordingLoopModel(ScriptedToolModel):
    script: list[Any] = Field(default_factory=list)
    seen: list[Any] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=tools, **kwargs)

    def _generate(self, messages, **kwargs):
        self.seen.append((list(messages), kwargs))
        assert self.script, "Unexpected extra model call"
        response = self.script.pop(0)
        if isinstance(response, Exception):
            raise response
        return ChatResult(generations=[ChatGeneration(message=response)])


def call(call_id, *, name="lookup", **args):
    return {"name": name, "args": args, "id": call_id}


def request(*calls):
    return AIMessage(content="", tool_calls=list(calls))


def build_loop(script, tools=()):
    model = RecordingLoopModel(responses=[], script=script)
    with patch("react_agent.llm_client", model):
        agent = build_react_agent("Use only tool evidence.", tools)
    return agent, model


def run_loop(agent, limit=24):
    return agent.invoke({"messages": [("human", "Find a matching course.")]},
                        config={"recursion_limit": limit})


def corrections(model):
    return [messages for messages, _ in model.seen if any(
        isinstance(m, SystemMessage) and "Runtime loop correction" in m.content
        for m in messages
    )]


def final_calls(model):
    return [messages for messages, kwargs in model.seen if "tools" not in kwargs]


def assert_protocol(messages):
    pending = set()
    for message in messages:
        if isinstance(message, AIMessage):
            assert not pending
            pending = {tc["id"] for tc in message.tool_calls}
        elif isinstance(message, ToolMessage):
            assert message.tool_call_id in pending
            pending.remove(message.tool_call_id)
    assert not pending


@pytest.fixture
def lookup_calls():
    calls = []

    @tool
    def lookup(page: int = 1) -> list:
        """Look up courses in a local fixture."""
        calls.append(page)
        return []

    return lookup, calls


def test_repeat_correction_then_block_with_native_protocol(lookup_calls, caplog):
    caplog.set_level(logging.INFO, logger="college_advisor")
    lookup, calls = lookup_calls
    agent, model = build_loop([
        request(call("one")), request(call("two", page=1)), request(call("three", page="1")),
        request(call("blocked", page=1)), AIMessage(content="No matches for this query."),
    ], [lookup])
    result = run_loop(agent, limit=12)
    assert calls == [1, 1, 1]
    assert len(corrections(model)) == len(final_calls(model)) == 1
    assert result["messages"][-1].content == "No matches for this query."
    assert "react_guard" not in result and "remaining_steps" not in result
    blocked = next(m for m in result["messages"] if isinstance(m, ToolMessage)
                   and m.tool_call_id == "blocked")
    assert blocked.status == "error" and "not a search result" in blocked.content
    assert_protocol(result["messages"])
    assert "发出一次纠偏" in caplog.text and "停止搜索" in caplog.text
    assert "observation_tool_call_id" not in caplog.text and "No matches" not in caplog.text


def test_empty_result_can_end_without_retry(lookup_calls):
    lookup, calls = lookup_calls
    answer = "知识库里没有符合条件的答案"
    agent, model = build_loop([request(call("empty")), AIMessage(content=answer)], [lookup])
    result = run_loop(agent)
    observation = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert observation.content == [] and observation.status == "success"
    assert result["messages"][-1].content == answer and calls == [1]
    assert not corrections(model) and not final_calls(model)
    assert any(isinstance(m, SystemMessage) and answer in m.content
               for m in model.seen[-1][0])


@pytest.mark.parametrize("pages,expected_corrections,expected_final", [
    ([1, 1, 1, 2, 3], 1, 0),   # Correcting parameters must not reprocess old results.
    ([1, 1, 1, 2, 2, 2], 1, 1),
    ([1, 2, 1, 2, 1, 2], 1, 1),
    ([1, 2, 3, 4, 5], 0, 0),   # Ordinary pagination.
])
def test_correction_and_alternating_patterns(
    pages, expected_corrections, expected_final, lookup_calls,
):
    lookup, calls = lookup_calls
    agent, model = build_loop([
        *[request(call(str(n), page=page)) for n, page in enumerate(pages)],
        AIMessage(content="Finished with existing evidence."),
    ], [lookup])
    run_loop(agent)
    assert calls == pages
    assert len(corrections(model)) == expected_corrections
    assert len(final_calls(model)) == expected_final


@pytest.mark.parametrize("values,expected_corrections", [
    (["A", "A", "B", "A", "A"], 0),
    (['{"a":1,"b":2}', '{"b":2,"a":1}', '{"a":1, "b":2}'], 1),
    (["[1,2]", "[1,2]", "[2,1]"], 0),
    (["hello", "hello", '"hello"'], 0),
])
def test_result_comparison(values, expected_corrections):
    answers = iter(values)

    @tool
    def lookup() -> str:
        """Return a changing observation."""
        return next(answers)

    agent, model = build_loop([
        *[request(call(str(n))) for n in range(len(values))], AIMessage(content="Done."),
    ], [lookup])
    run_loop(agent)
    assert len(corrections(model)) == expected_corrections
    assert not final_calls(model)


def test_argument_validators_and_list_order_are_preserved():
    @tool(args_schema=GetCourseDetailsInput)
    def lookup(course_codes: list[str]) -> str:
        """Return catalog details."""
        return "Verified course details"

    for codes, expected in [
        ([["MATH416"], ["MATH 416"], ["math416"]], 1),
        ([["MATH 416", "CS 124"], ["MATH 416", "CS 124"], ["CS 124", "MATH 416"]], 0),
    ]:
        agent, model = build_loop([
            *[request(call(str(n), course_codes=value)) for n, value in enumerate(codes)],
            AIMessage(content="Done."),
        ], [lookup])
        run_loop(agent)
        assert len(corrections(model)) == expected


@pytest.mark.parametrize("error_kind", ["validation", "resource", "returned"])
def test_repeated_recoverable_errors_are_protected(error_kind):
    @tool
    def lookup(page: int, runtime: ToolRuntime) -> ToolMessage:
        """Return a known recoverable error."""
        if error_kind == "resource":
            raise ToolException("No stored resource")
        return ToolMessage(content="Unavailable", status="error", tool_call_id=runtime.tool_call_id)

    agent, model = build_loop([
        *[request(call(str(n), page="invalid" if error_kind == "validation" else 1))
          for n in range(4)], AIMessage(content="The requested resource is unavailable."),
    ], [lookup])
    result = run_loop(agent)
    assert len(corrections(model)) == len(final_calls(model)) == 1
    assert all(m.status == "error" for m in result["messages"] if isinstance(m, ToolMessage))
    assert_protocol(result["messages"])


@pytest.mark.parametrize("tool_name", ["lookup", "load_skill", "future_tool"])
def test_repeat_in_parallel_batch_blocks_entire_next_batch(tool_name):
    calls = []

    @tool(tool_name)
    def lookup(page: int = 1) -> list:
        """Exercise protection independent of tool name."""
        calls.append(page)
        return []

    agent, model = build_loop([
        request(*[call(str(n), name=tool_name) for n in range(3)]),
        request(call("new", name=tool_name, page=2), call("repeat", name=tool_name)),
        AIMessage(content="Search stopped with partial evidence."),
    ], [lookup])
    result = run_loop(agent)
    assert calls == [1, 1, 1]
    assert len(corrections(model)) == len(final_calls(model)) == 1
    assert_protocol(result["messages"])


def test_parallel_completion_order_does_not_change_streak():
    order = ["3", "2", "4", "1", "0"]
    events = {key: Event() for key in order}
    completions = []

    @tool
    def lookup(runtime: ToolRuntime) -> str:
        """Model order A,A,B,B,A; completion order B,B,A,A,A."""
        key = runtime.tool_call_id
        position = order.index(key)
        if position:
            assert events[order[position - 1]].wait(3)
        completions.append(key)
        events[key].set()
        return "A" if key in {"0", "1", "4"} else "B"

    agent, model = build_loop([
        request(*[call(str(n)) for n in range(5)]), AIMessage(content="Changed results."),
    ], [lookup])
    run_loop(agent)
    assert completions == order
    assert not corrections(model)


@pytest.mark.parametrize("limit", [2, 3, 4, 12, 24])
def test_existing_step_limit_reserves_one_answer(limit, lookup_calls):
    lookup, calls = lookup_calls
    ordinary_calls = limit // 2 - 1
    agent, model = build_loop([
        *[request(call(str(n), page=n)) for n in range(ordinary_calls)],
        AIMessage(content="Verified partial result and source."),
    ], [lookup])
    result = run_loop(agent, limit=limit)
    assert len(calls) == ordinary_calls
    assert len(model.seen) == ordinary_calls + 1
    assert len(final_calls(model)) == 1
    assert result["messages"][-1].content == "Verified partial result and source."
    assert_protocol(result["messages"])
    assert set(agent.get_graph().nodes) == {"__start__", "model", "tools", "__end__"}


@pytest.mark.parametrize("response", [AIMessage(content=""), request(call("forbidden"))])
def test_invalid_final_answer_stops_with_fixed_fallback(response, lookup_calls):
    lookup, calls = lookup_calls
    agent, model = build_loop([request(call("one")), response], [lookup])
    result = run_loop(agent, limit=4)
    assert result["messages"][-1].content == FINALIZATION_FALLBACK
    assert calls == [1] and len(model.seen) == 2
    assert_protocol(result["messages"])


@pytest.mark.parametrize("error", [TimeoutError("service failure"), ValueError("programming failure")])
@pytest.mark.parametrize("finishing", [False, True])
def test_model_failures_still_propagate(error, finishing, lookup_calls):
    lookup, _ = lookup_calls
    agent, model = build_loop([request(call("one")), error] if finishing else [error], [lookup])
    with pytest.raises(type(error)) as raised:
        run_loop(agent, limit=4)
    assert raised.value is error
    assert len(model.seen) == (2 if finishing else 1)


def test_new_invocation_excludes_history_and_resets_correction(lookup_calls):
    lookup, calls = lookup_calls
    agent, model = build_loop([
        *[request(call(str(n))) for n in range(3)], AIMessage(content="First answer."),
        *[request(call("next-" + str(n))) for n in range(3)], AIMessage(content="Second answer."),
    ], [lookup])
    first = run_loop(agent)
    second = agent.invoke({"messages": [*first["messages"], HumanMessage(content="New question.")]},
                          config={"recursion_limit": 24})
    assert second["messages"][-1].content == "Second answer."
    assert calls == [1] * 6
    assert len(corrections(model)) == 2 and not final_calls(model)


def test_concurrent_invocations_do_not_share_correction(lookup_calls):
    lookup, calls = lookup_calls

    class ConcurrentModel(RecordingLoopModel):
        def _generate(self, messages, **kwargs):
            count = sum(isinstance(m, ToolMessage) for m in messages)
            user = next(m.content for m in messages if isinstance(m, HumanMessage))
            answer = (request(call(f"{user}-{count}")) if "tools" in kwargs
                      else AIMessage(content="Finished " + user))
            return ChatResult(generations=[ChatGeneration(message=answer)])

    with patch("react_agent.llm_client", ConcurrentModel(responses=[])):
        agent = build_react_agent("Use tool evidence.", [lookup])
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda n: agent.invoke(
            {"messages": [("human", str(n))]}, config={"recursion_limit": 12},
        ), range(5)))
    assert len(calls) == 15
    assert [r["messages"][-1].content for r in results] == ["Finished " + str(n) for n in range(5)]
    for result in results:
        assert_protocol(result["messages"])


if __name__ == "__main__":
    unittest.main()

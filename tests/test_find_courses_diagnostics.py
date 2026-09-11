import json
import logging
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, field_validator

from Eval.diagnose_find_courses import DiagnosticGuardLogHandler, DiagnosticTraceHandler


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gen_ed: str

    @field_validator("gen_ed")
    @classmethod
    def normalize_gen_ed(cls, value: str) -> str:
        return value.strip()


@tool(args_schema=SearchInput)
def find_courses(gen_ed: str) -> list[dict[str, str]]:
    """Test-only search tool."""
    return [{"course_code": "AFRO 224", "credits": "3 Hours"}]


def _events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_trace_correlates_concurrent_tools_and_normalizes_inputs(tmp_path):
    path = tmp_path / "trace.jsonl"
    callback = DiagnosticTraceHandler(path, "test-run", [find_courses])
    first_id, second_id = uuid4(), uuid4()

    callback.on_tool_start(
        {"name": "find_courses"},
        '{"gen_ed": " US Minority "}',
        run_id=first_id,
        parent_run_id=uuid4(),
        metadata={"langgraph_node": "tools"},
        inputs={"gen_ed": " US Minority "},
    )
    callback.on_tool_start(
        {"name": "find_courses"},
        '{"gen_ed": "Humanities"}',
        run_id=second_id,
        parent_run_id=uuid4(),
        metadata={"langgraph_node": "tools"},
        inputs={"gen_ed": "Humanities"},
    )
    callback.on_tool_end(
        ToolMessage(
            content='[{"course_code":"AFRO 224","credits":"3 Hours"}]',
            name="find_courses",
            tool_call_id="second",
        ),
        run_id=second_id,
    )
    callback.on_tool_end(
        ToolMessage(
            content='[{"course_code":"LLS 100","credits":"3 Hours"}]',
            name="find_courses",
            tool_call_id="first",
        ),
        run_id=first_id,
    )

    events = _events(path)
    starts = {event["callback_run_id"]: event for event in events if event["event"] == "tool_start"}
    ends = {event["callback_run_id"]: event for event in events if event["event"] == "tool_end"}
    assert starts[str(first_id)]["raw_inputs"] == {"gen_ed": " US Minority "}
    assert starts[str(first_id)]["effective_inputs"] == {"gen_ed": "US Minority"}
    assert ends[str(first_id)]["tool"] == "find_courses"
    assert ends[str(second_id)]["tool"] == "find_courses"
    assert "LLS 100" in ends[str(first_id)]["output"]["content"]
    assert "AFRO 224" in ends[str(second_id)]["output"]["content"]


def test_trace_omits_non_search_tool_message_bodies(tmp_path):
    path = tmp_path / "trace.jsonl"
    callback = DiagnosticTraceHandler(path, "test-run", [find_courses])
    callback.on_chat_model_start(
        {},
        [[ToolMessage(content="private full skill body", name="load_skill", tool_call_id="skill")]],
        run_id=uuid4(),
        metadata={"langgraph_node": "model"},
    )

    message = _events(path)[0]["messages"][0][0]
    assert message["content"]["omitted"] is True
    assert "private full skill body" not in json.dumps(message)


def test_guard_events_are_added_to_the_same_trace(tmp_path):
    path = tmp_path / "trace.jsonl"
    callback = DiagnosticTraceHandler(path, "test-run", [find_courses])
    handler = DiagnosticGuardLogHandler(callback)
    record = logging.LogRecord(
        name="college_advisor.react_agent.guard",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="ReAct 发现重复，发出一次纠偏",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    event = _events(path)[0]
    assert event["event"] == "guard_log"
    assert event["level"] == "WARNING"
    assert event["message"] == "ReAct 发现重复，发出一次纠偏"

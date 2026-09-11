"""Capture a structured trace for the repeated find_courses investigation.

This runner observes the existing graph through LangChain callbacks. It does not
change prompts, tool inputs, tool outputs, or agent control flow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from time import perf_counter, time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

USER_INPUT = "给我推几门gpa很高的gen ed，我要us minority 的"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseMessage):
        return _message_record(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    return repr(value)


def _content_record(message: BaseMessage) -> Any:
    content = _jsonable(message.content)
    if isinstance(message, SystemMessage):
        rendered = json.dumps(content, ensure_ascii=False, sort_keys=True)
        return {"omitted": True, "characters": len(rendered), "sha256": _digest(rendered)}
    if isinstance(message, ToolMessage) and message.name != "find_courses":
        rendered = json.dumps(content, ensure_ascii=False, sort_keys=True)
        return {
            "omitted": True,
            "characters": len(rendered),
            "sha256": _digest(rendered),
        }
    return content


def _message_record(message: BaseMessage) -> dict[str, Any]:
    record: dict[str, Any] = {
        "type": message.type,
        "name": getattr(message, "name", None),
        "content": _content_record(message),
    }
    if isinstance(message, AIMessage):
        record["tool_calls"] = _jsonable(message.tool_calls)
        record["invalid_tool_calls"] = _jsonable(message.invalid_tool_calls)
    if isinstance(message, ToolMessage):
        record["tool_call_id"] = message.tool_call_id
        record["status"] = message.status
    return record


class DiagnosticTraceHandler(BaseCallbackHandler):
    """Write model and tool events as concurrency-safe JSON Lines."""

    def __init__(self, path: Path, run_label: str, tools: list[Any]) -> None:
        self.path = path
        self.run_label = run_label
        self._lock = threading.RLock()
        self._model_rounds: defaultdict[str, int] = defaultdict(int)
        self._model_runs: dict[str, tuple[str, int]] = {}
        self._tool_runs: dict[str, dict[str, Any]] = {}
        self._tool_schemas = {
            tool.name: tool.get_input_schema() for tool in tools
        }

    def _write(self, event: str, **data: Any) -> None:
        record = {
            "event": event,
            "timestamp": time(),
            "run_label": self.run_label,
            **_jsonable(data),
        }
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")

    @staticmethod
    def _node(metadata: dict[str, Any] | None) -> str:
        if not metadata:
            return "unknown"
        return str(metadata.get("langgraph_node", metadata.get("checkpoint_ns", "unknown")))

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        node = self._node(metadata)
        with self._lock:
            self._model_rounds[node] += 1
            round_number = self._model_rounds[node]
            self._model_runs[str(run_id)] = (node, round_number)
        self._write(
            "model_start",
            callback_run_id=str(run_id),
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            node=node,
            model_round=round_number,
            messages=[[_message_record(message) for message in batch] for batch in messages],
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        node, round_number = self._model_runs.get(str(run_id), ("unknown", 0))
        generations = []
        for batch in response.generations:
            generations.append([
                _message_record(generation.message)
                if hasattr(generation, "message")
                else _jsonable(generation)
                for generation in batch
            ])
        self._write(
            "model_end",
            callback_run_id=str(run_id),
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            node=node,
            model_round=round_number,
            generations=generations,
        )

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        name = str(serialized.get("name", "unknown"))
        raw_inputs = inputs if inputs is not None else input_str
        effective_inputs: Any = raw_inputs
        validation_error = None
        schema = self._tool_schemas.get(name)
        if schema is not None and isinstance(raw_inputs, dict):
            try:
                effective_inputs = schema.model_validate(raw_inputs).model_dump(mode="json")
            except Exception as error:  # The runtime remains responsible for handling it.
                validation_error = f"{type(error).__name__}: {error}"
        tool_record = {
            "tool": name,
            "node": self._node(metadata),
            "started": perf_counter(),
            "raw_inputs": raw_inputs,
            "effective_inputs": effective_inputs,
            "validation_error": validation_error,
        }
        with self._lock:
            self._tool_runs[str(run_id)] = tool_record
        self._write(
            "tool_start",
            callback_run_id=str(run_id),
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            **{key: value for key, value in tool_record.items() if key != "started"},
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        tool_record = self._tool_runs.get(str(run_id), {})
        self._write(
            "tool_end",
            callback_run_id=str(run_id),
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            tool=tool_record.get("tool", "unknown"),
            node=tool_record.get("node", "unknown"),
            elapsed_seconds=(
                perf_counter() - tool_record["started"] if "started" in tool_record else None
            ),
            output=output,
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        tool_record = self._tool_runs.get(str(run_id), {})
        self._write(
            "tool_error",
            callback_run_id=str(run_id),
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            tool=tool_record.get("tool", "unknown"),
            node=tool_record.get("node", "unknown"),
            elapsed_seconds=(
                perf_counter() - tool_record["started"] if "started" in tool_record else None
            ),
            error_type=type(error).__name__,
            error=str(error),
        )


class DiagnosticGuardLogHandler(logging.Handler):
    """Copy guard correction/block events into the structured trace."""

    def __init__(self, trace: DiagnosticTraceHandler) -> None:
        super().__init__(level=logging.INFO)
        self.trace = trace

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == "college_advisor.react_agent.guard":
            self.trace._write(
                "guard_log",
                level=record.levelname,
                message=record.getMessage(),
            )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "Eval" / "diagnostics",
    )
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_path = args.output_dir / f"find_courses_trace_{timestamp}.jsonl"
    result_path = args.output_dir / f"find_courses_results_{timestamp}.json"

    from graph import graph
    from nodes.advising import ADVISING_TOOLS

    logger = logging.getLogger("college_advisor")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)

    results = []
    for index in range(1, args.runs + 1):
        run_label = f"reproduction-{index}"
        callback = DiagnosticTraceHandler(trace_path, run_label, ADVISING_TOOLS)
        guard_log_handler = DiagnosticGuardLogHandler(callback)
        guard_logger = logging.getLogger("college_advisor.react_agent.guard")
        guard_logger.addHandler(guard_log_handler)
        started = perf_counter()
        try:
            result = graph.invoke(
                {"current_input": USER_INPUT, "messages": []},
                context={"profile": None},
                config={"callbacks": [callback]},
            )
        finally:
            guard_logger.removeHandler(guard_log_handler)
        results.append(
            {
                "run_label": run_label,
                "elapsed_seconds": perf_counter() - started,
                "route": result.get("route"),
                "request_brief": result.get("request_brief"),
                "response": result.get("response"),
            }
        )
        print(f"{run_label}: {results[-1]['elapsed_seconds']:.2f}s", flush=True)

    result_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"trace: {trace_path}")
    print(f"results: {result_path}")


if __name__ == "__main__":
    main()

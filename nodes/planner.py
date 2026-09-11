import json
import logging
from pathlib import Path
from time import perf_counter

from langchain_core.messages import HumanMessage, convert_to_openai_messages

from client.llm_client import llm_client
from state import AdvisorState


logger = logging.getLogger(f"college_advisor.{__name__}")

PLANNER_SYSTEM_PROMPT = (
    Path(__file__).resolve().parents[1]
    / "prompt"
    / "planner_prompt.txt"
).read_text(encoding="utf-8").strip()


def planner(state: AdvisorState) -> dict[str, str]:
    """Rewrite the request while preserving raw input, history, and route."""
    started = perf_counter()
    logger.info("Planner 开始")
    payload = {
        "conversation_context": convert_to_openai_messages(state.get("messages", [])),
        "current_input": state["current_input"],
    }
    response = llm_client.invoke(
        [
            ("system", PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
    )
    logger.info("Planner 完成，耗时 %.2fs", perf_counter() - started)
    return {"request_brief": response.content.strip()}


__all__ = ["PLANNER_SYSTEM_PROMPT", "planner"]

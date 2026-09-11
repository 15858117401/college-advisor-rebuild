import logging
from time import perf_counter

from client.llm_client import llm_client
from state import AdvisorState


logger = logging.getLogger(f"college_advisor.{__name__}")

PLANNER_SYSTEM_PROMPT = "Do not do anything. Do not change anything."


def planner(state: AdvisorState) -> dict:
    """Run the placeholder planner without changing graph state."""
    started = perf_counter()
    logger.info("Planner 开始")
    llm_client.invoke(
        [
            ("system", PLANNER_SYSTEM_PROMPT),
            ("human", state["current_input"]),
        ]
    )
    logger.info("Planner 完成，耗时 %.2fs", perf_counter() - started)
    return {}


__all__ = ["PLANNER_SYSTEM_PROMPT", "planner"]

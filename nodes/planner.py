from client.llm_client import llm_client
from state import AdvisorState


PLANNER_SYSTEM_PROMPT = "Do not do anything. Do not change anything."


def planner(state: AdvisorState) -> dict:
    """Run the placeholder planner without changing graph state."""
    llm_client.invoke(
        [
            ("system", PLANNER_SYSTEM_PROMPT),
            ("human", state["current_input"]),
        ]
    )
    return {}


__all__ = ["PLANNER_SYSTEM_PROMPT", "planner"]

from typing import Literal

from state import AdvisorState


def execute_tasks(state: AdvisorState) -> dict:
    """Placeholder for executing planned advising tasks."""
    return {}


def route_after_execution(
    state: AdvisorState,
) -> Literal["clarify", "compose_response"]:
    # TODO: Route to clarify when task execution requires user input.
    return "compose_response"

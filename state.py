from typing import Literal, NotRequired

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import MessagesState


Route = Literal[
    "clarify",
    "catalog_lookup",
    "advising",
    "out_of_scope",
]


class AdvisorState(MessagesState):
    current_input: str
    route: NotRequired[Route]
    response: NotRequired[str]


def messages_with_current_input(state: AdvisorState) -> list[BaseMessage]:
    """Combine past messages with the current input for an agent call."""
    return [
        *state.get("messages", []),
        HumanMessage(content=state["current_input"]),
    ]


__all__ = ["AdvisorState", "Route", "messages_with_current_input"]

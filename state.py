from typing import Literal, NotRequired

from langgraph.graph import MessagesState


Route = Literal[
    "clarify",
    "catalog_lookup",
    "advising",
    "out_of_scope",
]


class AdvisorState(MessagesState):
    route: NotRequired[Route]
    response: NotRequired[str]


__all__ = ["AdvisorState", "Route"]

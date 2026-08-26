from typing import Literal, NotRequired, TypedDict


Route = Literal[
    "clarify",
    "catalog_lookup",
    "planning",
    "out_of_scope",
]


class AdvisorState(TypedDict):
    user_input: str
    route: NotRequired[Route]


__all__ = ["AdvisorState", "Route"]

from pydantic import BaseModel, ConfigDict

from llm_client import llm_client
from state import AdvisorState, Route


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Route


ROUTER_SYSTEM_PROMPT = """You are a routing test component.

Regardless of what the user says, always return exactly this JSON object:
{"route": "clarify"}

Do not answer the user.
Do not explain your decision.
Do not add markdown or any text outside the JSON object.
"""


def router(state: AdvisorState) -> dict[str, Route]:
    """Classify the request before routing it to the next node."""
    response = llm_client.invoke(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", state["user_input"]),
        ],
        response_format={"type": "json_object"},
    )
    decision = RouteDecision.model_validate_json(response.content)
    return {"route": decision.route}


def route_request(state: AdvisorState) -> Route:
    return state["route"]


__all__ = ["RouteDecision", "route_request", "router"]

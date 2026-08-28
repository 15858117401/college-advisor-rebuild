from pydantic import BaseModel, ConfigDict

from client.llm_client import llm_client
from state import AdvisorState, Route


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Route


ROUTER_SYSTEM_PROMPT = """You are the intent router for a college-advising agent.

For the current version of the agent, catalog_lookup is the only available intent.
Regardless of what the user asks, you must always route the request to catalog_lookup.

Return exactly this JSON object:
{"route": "catalog_lookup"}

Do not answer the user.
Do not explain your decision.
Do not add markdown or any text outside the JSON object.
"""


def router(state: AdvisorState) -> dict[str, Route]:
    """Classify the request before routing it to the next node."""
    current_message = state["messages"][-1]
    response = llm_client.invoke(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", current_message.content),
        ],
        response_format={"type": "json_object"},
    )
    decision = RouteDecision.model_validate_json(response.content)
    return {"route": decision.route}


def route_request(state: AdvisorState) -> Route:
    return state["route"]


__all__ = ["RouteDecision", "route_request", "router"]

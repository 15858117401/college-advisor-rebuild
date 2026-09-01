import json
from pathlib import Path

from langchain_core.messages import HumanMessage, convert_to_openai_messages
from pydantic import BaseModel, ConfigDict

from client.llm_client import llm_client
from state import AdvisorState, Route


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Route


ROUTER_SYSTEM_PROMPT = (
    Path(__file__).resolve().parents[1]
    / "prompt"
    / "system_prompt.txt"
).read_text(encoding="utf-8")


def _router_input(state: AdvisorState) -> str:
    return json.dumps(
        {
            "conversation_context": convert_to_openai_messages(
                state.get("messages", [])
            ),
            "current_input": state["current_input"],
        },
        ensure_ascii=False,
    )


def router(state: AdvisorState) -> dict[str, Route]:
    """Classify the request before routing it to the next node."""
    response = llm_client.invoke(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=_router_input(state)),
        ],
        response_format={"type": "json_object"},
    )
    decision = RouteDecision.model_validate_json(response.content)
    return {"route": decision.route}


def route_request(state: AdvisorState) -> Route:
    return state["route"]


__all__ = ["RouteDecision", "route_request", "router"]

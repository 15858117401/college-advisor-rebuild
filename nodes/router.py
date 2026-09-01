import json
from pathlib import Path

from langchain_core.messages import HumanMessage, convert_to_openai_messages
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict

from client.llm_client import llm_client
from state import (
    AdvisorContext,
    AdvisorState,
    Route,
    StudentProfile,
    profile_from_runtime,
)


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Route


ROUTER_SYSTEM_PROMPT = (
    Path(__file__).resolve().parents[1]
    / "prompt"
    / "system_prompt.txt"
).read_text(encoding="utf-8")


def _router_input(state: AdvisorState, profile: StudentProfile) -> str:
    return json.dumps(
        {
            "conversation_context": convert_to_openai_messages(
                state.get("messages", [])
            ),
            "current_input": state["current_input"],
            "profile": profile,
        },
        ensure_ascii=False,
    )


def router(
    state: AdvisorState,
    runtime: Runtime[AdvisorContext] | None = None,
) -> dict[str, Route]:
    """Classify the request before routing it to the next node."""
    profile = profile_from_runtime(runtime)
    response = llm_client.invoke(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=_router_input(state, profile)),
        ],
        response_format={"type": "json_object"},
    )
    decision = RouteDecision.model_validate_json(response.content)
    return {"route": decision.route}


def route_request(state: AdvisorState) -> Route:
    return state["route"]


__all__ = ["RouteDecision", "route_request", "router"]

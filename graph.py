from typing import Literal, NotRequired, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


Route = Literal[
    "clarify",
    "catalog_lookup",
    "planning",
    "out_of_scope",
]


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Route


class AdvisorState(TypedDict):
    user_input: str
    route: NotRequired[Route]


ROUTER_SYSTEM_PROMPT = """You are a routing test component.

Regardless of what the user says, always return exactly this JSON object:
{"route": "clarify"}

Do not answer the user.
Do not explain your decision.
Do not add markdown or any text outside the JSON object.
"""


router_model = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=DEEPSEEK_MODEL,
    temperature=0,
).bind(response_format={"type": "json_object"})


def router(state: AdvisorState) -> dict[str, Route]:
    """Classify the request before routing it to the next node."""
    response = router_model.invoke(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", state["user_input"]),
        ]
    )
    decision = RouteDecision.model_validate_json(response.content)
    return {"route": decision.route}


def clarify(state: AdvisorState) -> dict:
    """Placeholder for asking the user to clarify their request."""
    return {}


def catalog_lookup(state: AdvisorState) -> dict:
    """Placeholder for factual catalog lookup."""
    return {}


def planning(state: AdvisorState) -> dict:
    """Placeholder for building one or more advising tasks."""
    return {}


def execute_tasks(state: AdvisorState) -> dict:
    """Placeholder for executing planned advising tasks."""
    return {}


def compose_response(state: AdvisorState) -> dict:
    """Placeholder for composing the final response."""
    return {}


def out_of_scope(state: AdvisorState) -> dict:
    """Placeholder for handling requests outside the advisor's scope."""
    return {}


def route_request(state: AdvisorState) -> Route:
    return state["route"]


def route_after_execution(
    state: AdvisorState,
) -> Literal["clarify", "compose_response"]:
    # TODO: Route to clarify when task execution requires user input.
    return "compose_response"


def build_graph():
    builder = StateGraph(AdvisorState)

    builder.add_node("router", router)
    builder.add_node("clarify", clarify)
    builder.add_node("catalog_lookup", catalog_lookup)
    builder.add_node("planning", planning)
    builder.add_node("execute_tasks", execute_tasks)
    builder.add_node("compose_response", compose_response)
    builder.add_node("out_of_scope", out_of_scope)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        route_request,
        {
            "clarify": "clarify",
            "catalog_lookup": "catalog_lookup",
            "planning": "planning",
            "out_of_scope": "out_of_scope",
        },
    )
    builder.add_edge("clarify", END)
    builder.add_edge("catalog_lookup", "compose_response")
    builder.add_edge("planning", "execute_tasks")
    builder.add_conditional_edges(
        "execute_tasks",
        route_after_execution,
        {
            "clarify": "clarify",
            "compose_response": "compose_response",
        },
    )
    builder.add_edge("compose_response", END)
    builder.add_edge("out_of_scope", END)

    return builder.compile()


graph = build_graph()


__all__ = [
    "AdvisorState",
    "Route",
    "RouteDecision",
    "build_graph",
    "graph",
]

from langgraph.graph import END, START, StateGraph

from nodes import (
    RouteDecision,
    catalog_lookup,
    clarify,
    compose_response,
    execute_tasks,
    out_of_scope,
    planning,
    route_after_execution,
    route_request,
    router,
)
from state import AdvisorState, Route


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

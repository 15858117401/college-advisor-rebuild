from langgraph.graph import END, START, StateGraph

from nodes import (
    RouteDecision,
    advising,
    catalog_lookup,
    clarify,
    compose_response,
    out_of_scope,
    route_request,
    router,
)
from state import AdvisorState, Route


def build_graph():
    builder = StateGraph(AdvisorState)

    builder.add_node("router", router)
    builder.add_node("clarify", clarify)
    builder.add_node("catalog_lookup", catalog_lookup)
    builder.add_node("advising", advising)
    builder.add_node("compose_response", compose_response)
    builder.add_node("out_of_scope", out_of_scope)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        route_request,
        {
            "clarify": "clarify",
            "catalog_lookup": "catalog_lookup",
            "advising": "advising",
            "out_of_scope": "out_of_scope",
        },
    )
    builder.add_edge("clarify", END)
    builder.add_edge("catalog_lookup", "compose_response")
    builder.add_edge("advising", "compose_response")
    builder.add_edge("out_of_scope", "compose_response")
    builder.add_edge("compose_response", END)

    return builder.compile()


graph = build_graph()


__all__ = [
    "AdvisorState",
    "Route",
    "RouteDecision",
    "build_graph",
    "graph",
]

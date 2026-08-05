"""Minimal DeepSeek-to-LangGraph binding for the rebuild."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, MessagesState, StateGraph

from app.llm_client import build_deepseek_llm


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Load the local key and initialize DeepSeek on first invocation."""

    return build_deepseek_llm()


def build_graph(llm: BaseChatModel | None = None):
    """Build the baseline graph; future advisor nodes can extend this graph."""

    def call_deepseek(state: MessagesState):
        active_llm = llm or get_llm()
        return {"messages": [active_llm.invoke(state["messages"])]}

    builder = StateGraph(MessagesState)
    builder.add_node("deepseek", call_deepseek)
    builder.add_edge(START, "deepseek")
    builder.add_edge("deepseek", END)
    return builder.compile()


# `langgraph dev` imports this object through langgraph.json. Client creation is
# lazy, so the graph can be imported and visualized without reading the API key.
graph = build_graph()

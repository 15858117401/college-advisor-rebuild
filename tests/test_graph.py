from __future__ import annotations

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.graph import build_graph


def test_graph_is_bound_to_chat_model() -> None:
    graph = build_graph(FakeListChatModel(responses=["configured"]))

    result = graph.invoke({"messages": [{"role": "user", "content": "hello"}]})

    assert result["messages"][-1].content == "configured"

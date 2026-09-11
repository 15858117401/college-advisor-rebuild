from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_home_serves_the_chat_interface() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "College Advisor" in response.text
    assert 'fetch("/chat"' in response.text


@patch("main.graph.invoke")
def test_chat_returns_the_graph_response(invoke) -> None:
    invoke.return_value = {"response": "Try STAT 410."}

    response = client.post("/chat", json={"text": "What should I take?"})

    assert response.status_code == 200
    assert response.json() == {"response": "Try STAT 410."}
    invoke.assert_called_once_with(
        {"current_input": "What should I take?", "messages": []},
        context={"profile": None},
    )


def test_chat_rejects_an_overlong_prompt() -> None:
    response = client.post("/chat", json={"text": "x" * 2001})

    assert response.status_code == 422

from client.llm_client import llm_client
from state import AdvisorState


COMPOSE_SYSTEM_PROMPT = """Rewrite the provided draft as a clear, concise, human-readable answer.
Preserve the facts in the draft and do not add new information.
Return only the final answer.
"""


def compose_response(state: AdvisorState) -> dict:
    """Rewrite a node result into the final user-facing response."""
    response = llm_client.invoke(
        [
            ("system", COMPOSE_SYSTEM_PROMPT),
            ("human", state["response"]),
        ]
    )
    return {"response": response.content}


__all__ = ["COMPOSE_SYSTEM_PROMPT", "compose_response"]

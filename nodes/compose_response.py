import json

from langchain_core.messages import convert_to_messages

from client.llm_client import llm_client
from state import AdvisorState


COMPOSE_SYSTEM_PROMPT = """You are an academic advisor composing the final student-facing answer.
Use current_input as the request, conversation_context only to resolve references,
and draft only as source material. Answer every requested part directly with the
minimum supported information. Do not add facts, superlatives, or certainty beyond
the draft, and do not answer adjacent questions the student did not ask.


For a conflict-free proposed schedule, give one compact table containing only the
course, section, and meeting days/times, followed by “No swap is needed.” Retain
only an essential linked-section or uncertainty caveat. If a pairing is inferred,
label it as inferred and say to confirm it. Do not add prerequisites, credit totals,
a day-by-day restatement, alternatives, or hypothetical swaps.

Retain evidence and attribution only when they materially affect the requested
answer. Preserve source URLs and sample-size caveats when material. Report
unavailable evidence simply as unavailable; never describe how it was searched,
found, captured, or retrieved. Omit greetings,
introductions, internal reasoning, searches, tool activity, planning, deliberation,
rejected choices, repetition, unnecessary background, speculative alternatives,
and unsolicited offers. Prefer a few sentences or a compact table. Begin with the
substantive answer, not a meta-summary or a heading that merely restates the
subject. Return only the student-facing answer.
"""


def compose_response(state: AdvisorState) -> dict:
    """Edit the draft to answer the current request without unnecessary material."""
    payload = {
        "current_input": state["current_input"],
        "conversation_context": [
            {"role": message.type, "content": message.content}
            for message in convert_to_messages(state.get("messages", []))
        ],
        "draft": state["response"],
    }
    response = llm_client.invoke(
        [
            ("system", COMPOSE_SYSTEM_PROMPT),
            ("human", json.dumps(payload, ensure_ascii=False)),
        ]
    )
    return {"response": response.content}


__all__ = ["COMPOSE_SYSTEM_PROMPT", "compose_response"]

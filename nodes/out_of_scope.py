from state import AdvisorState


OUT_OF_SCOPE_RESPONSE = "This is beyond the conversation"


def out_of_scope(state: AdvisorState) -> dict[str, str]:
    """Return the fixed out-of-scope draft for response composition."""
    return {"response": OUT_OF_SCOPE_RESPONSE}


__all__ = ["OUT_OF_SCOPE_RESPONSE", "out_of_scope"]

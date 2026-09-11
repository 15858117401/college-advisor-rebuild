import logging
from time import perf_counter

from state import AdvisorState


logger = logging.getLogger(f"college_advisor.{__name__}")

OUT_OF_SCOPE_RESPONSE = "This is beyond the conversation"


def out_of_scope(state: AdvisorState) -> dict[str, str]:
    """Return the fixed out-of-scope draft for response composition."""
    started = perf_counter()
    logger.info("Out of Scope 开始")
    logger.info("Out of Scope 完成，耗时 %.2fs", perf_counter() - started)
    return {"response": OUT_OF_SCOPE_RESPONSE}


__all__ = ["OUT_OF_SCOPE_RESPONSE", "out_of_scope"]

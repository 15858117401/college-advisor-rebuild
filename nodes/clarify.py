import logging
from time import perf_counter

from state import AdvisorState


logger = logging.getLogger(f"college_advisor.{__name__}")


def clarify(state: AdvisorState) -> dict:
    """Placeholder for asking the user to clarify their request."""
    started = perf_counter()
    logger.info("Clarify 开始（占位节点）")
    logger.info("Clarify 完成（占位节点），耗时 %.2fs", perf_counter() - started)
    return {}

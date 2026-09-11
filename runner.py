import logging
from time import perf_counter

from graph import graph


USER_INPUT = "给我推几门gpa很高的gen ed，我要us minority 的"


if __name__ == "__main__":
    logger = logging.getLogger("college_advisor")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)

    started = perf_counter()
    logger.info("流程开始")
    try:
        result = graph.invoke(
            {"current_input": USER_INPUT, "messages": []},
            context={"profile": None},
        )
    except Exception:
        logger.exception("流程失败，耗时 %.2fs", perf_counter() - started)
        raise
    logger.info("流程完成，总耗时 %.2fs", perf_counter() - started)
    print(result.get("response", ""))

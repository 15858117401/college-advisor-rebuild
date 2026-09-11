import logging
from time import perf_counter

from graph import graph


USER_INPUT = "帮我找 3 门三学分课程：其中 2 门属于 Cultural Studies - Non-West，1 门属于 Humanities - Lit & Arts；课程编号必须在 200–399 之间，历史课程 GPA 至少 3.5。比较它们的先修要求，并检查 Spring 2026 是否有班次。"


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

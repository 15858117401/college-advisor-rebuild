"""Read-only pagination for agent resource queries."""
from collections.abc import Callable
from typing import Any


def fetch_all_rows(query_factory: Callable[[], Any], *, page_size: int = 500) -> list[dict]:
    """Fetch an explicitly ordered query in pages below the Data API row limit."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = query_factory().range(offset, offset + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size

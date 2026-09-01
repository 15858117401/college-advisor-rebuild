import os
from typing import Any
from urllib.parse import urlsplit

import httpx


TAVILY_SEARCH_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT_SECONDS = 15
DEFAULT_MAX_RESULTS = 5
RETRYABLE_STATUS_CODES = {429}


def _error(error_type: str, message: str) -> dict[str, Any]:
    return {
        "results": [],
        "error": {
            "type": error_type,
            "message": message,
        },
    }


def _is_allowed_domain(url: str, allowed_domains: list[str]) -> bool:
    try:
        parsed_url = urlsplit(url)
        if parsed_url.scheme.casefold() not in {"http", "https"}:
            return False
        hostname = (parsed_url.hostname or "").casefold().rstrip(".")
    except ValueError:
        return False

    return any(
        hostname == domain.casefold().rstrip(".")
        or hostname.endswith(f".{domain.casefold().rstrip('.')}")
        for domain in allowed_domains
    )


def _normalize_results(
    raw_results: list[Any],
    allowed_domains: list[str],
    max_results: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue

        url = raw_result.get("url")
        if (
            not isinstance(url, str)
            or not url
            or url in seen_urls
            or not _is_allowed_domain(url, allowed_domains)
        ):
            continue

        title = raw_result.get("title")
        content = raw_result.get("content")
        result: dict[str, Any] = {
            "title": title if isinstance(title, str) else "",
            "url": url,
            "content": content if isinstance(content, str) else "",
        }

        score = raw_result.get("score")
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            result["score"] = score

        results.append(result)
        seen_urls.add(url)
        if len(results) == max_results:
            break

    return results


def search_tavily(
    query: str,
    *,
    include_domains: list[str],
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:
    """Search Tavily and return normalized results or a structured error."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return _error(
            "configuration_error",
            "TAVILY_API_KEY is required for professor research.",
        )

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_domains": include_domains,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response: httpx.Response | None = None
    for attempt in range(2):
        try:
            response = httpx.post(
                TAVILY_SEARCH_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except httpx.RequestError:
            return _error("request_failed", "Tavily request failed.")

        retryable = (
            response.status_code in RETRYABLE_STATUS_CODES
            or response.status_code >= 500
        )
        if retryable and attempt == 0:
            continue
        break

    if response is None or not 200 <= response.status_code < 300:
        status_code = response.status_code if response is not None else "unknown"
        return _error(
            "request_failed",
            f"Tavily returned HTTP {status_code}.",
        )

    try:
        data = response.json()
    except ValueError:
        return _error("invalid_response", "Tavily returned invalid JSON.")

    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        return _error(
            "invalid_response",
            "Tavily response did not contain a results list.",
        )

    return {
        "results": _normalize_results(
            data["results"],
            include_domains,
            max_results,
        )
    }


__all__ = ["search_tavily"]

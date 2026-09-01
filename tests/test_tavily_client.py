import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from client.tavily_client import (
    REQUEST_TIMEOUT_SECONDS,
    TAVILY_SEARCH_URL,
    search_tavily,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=None) -> None:
        self.status_code = status_code
        self.payload = payload if payload is not None else {"results": []}
        self.json_error = json_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class TavilyClientTest(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch("client.tavily_client.httpx.post")
    def test_missing_api_key_returns_configuration_error(self, post) -> None:
        result = search_tavily("Albert Yu", include_domains=["reddit.com"])

        post.assert_not_called()
        self.assertEqual(result["results"], [])
        self.assertEqual(result["error"]["type"], "configuration_error")
        self.assertNotIn("Bearer", str(result))

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-secret"}, clear=True)
    @patch("client.tavily_client.httpx.post")
    def test_builds_request_and_normalizes_allowed_results(self, post) -> None:
        post.return_value = FakeResponse(
            payload={
                "results": [
                    {
                        "title": "Albert Yu at UIUC",
                        "url": "https://www.ratemyprofessors.com/professor/1",
                        "content": "UIUC ratings",
                        "score": 0.9,
                    },
                    {
                        "title": "Duplicate",
                        "url": "https://www.ratemyprofessors.com/professor/1",
                        "content": "duplicate",
                    },
                    {
                        "title": "Wrong domain",
                        "url": "https://ratemyprofessors.com.evil.example/professor/1",
                        "content": "bad",
                    },
                    {
                        "title": "Wrong scheme",
                        "url": "javascript://ratemyprofessors.com/professor/2",
                        "content": "bad",
                    },
                ]
            }
        )

        result = search_tavily(
            "Albert Yu",
            include_domains=["ratemyprofessors.com"],
        )

        self.assertEqual(
            result,
            {
                "results": [
                    {
                        "title": "Albert Yu at UIUC",
                        "url": "https://www.ratemyprofessors.com/professor/1",
                        "content": "UIUC ratings",
                        "score": 0.9,
                    }
                ]
            },
        )
        kwargs = post.call_args.kwargs
        self.assertEqual(post.call_args.args[0], TAVILY_SEARCH_URL)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-secret")
        self.assertEqual(kwargs["timeout"], REQUEST_TIMEOUT_SECONDS)
        self.assertEqual(
            kwargs["json"],
            {
                "query": "Albert Yu",
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": False,
                "include_raw_content": False,
                "include_domains": ["ratemyprofessors.com"],
            },
        )

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-secret"}, clear=True)
    @patch("client.tavily_client.httpx.post")
    def test_retries_once_for_retryable_status(self, post) -> None:
        post.side_effect = [
            FakeResponse(status_code=429),
            FakeResponse(payload={"results": []}),
        ]

        result = search_tavily("Albert Yu", include_domains=["reddit.com"])

        self.assertEqual(result, {"results": []})
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0], post.call_args_list[1])

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-secret"}, clear=True)
    @patch("client.tavily_client.httpx.post")
    def test_reports_exhausted_retry_without_response_body(self, post) -> None:
        post.side_effect = [
            FakeResponse(status_code=503),
            FakeResponse(status_code=503, payload={"secret": "response-body"}),
        ]

        result = search_tavily("Albert Yu", include_domains=["reddit.com"])

        self.assertEqual(result["error"]["type"], "request_failed")
        self.assertIn("503", result["error"]["message"])
        self.assertNotIn("response-body", str(result))

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-secret"}, clear=True)
    @patch("client.tavily_client.httpx.post")
    def test_request_exception_returns_safe_error(self, post) -> None:
        post.side_effect = httpx.ConnectError("contains test-secret")

        result = search_tavily("Albert Yu", include_domains=["reddit.com"])

        self.assertEqual(result["error"]["type"], "request_failed")
        self.assertNotIn("test-secret", str(result))

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-secret"}, clear=True)
    @patch("client.tavily_client.httpx.post")
    def test_invalid_json_returns_invalid_response(self, post) -> None:
        post.return_value = FakeResponse(json_error=ValueError("bad json"))

        result = search_tavily("Albert Yu", include_domains=["reddit.com"])

        self.assertEqual(result["error"]["type"], "invalid_response")

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-secret"}, clear=True)
    @patch("client.tavily_client.httpx.post")
    def test_missing_results_list_returns_invalid_response(self, post) -> None:
        post.return_value = FakeResponse(payload={"results": "not-a-list"})

        result = search_tavily("Albert Yu", include_domains=["reddit.com"])

        self.assertEqual(result["error"]["type"], "invalid_response")


if __name__ == "__main__":
    unittest.main()

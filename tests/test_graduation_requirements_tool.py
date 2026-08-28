import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.graduation_requirements_tool import (
    LAS_DOCUMENT_KEY,
    MAJOR_DOCUMENT_KEYS,
    TABLE_NAME,
    get_graduation_requirements,
)


class _FakeTableQuery:
    def __init__(self, client, rows: list[dict]) -> None:
        self.client = client
        self.rows = rows

    def select(self, fields: str):
        self.client.calls.append(("select", fields))
        return self

    def in_(self, column: str, values: list[str]):
        self.client.calls.append(("in", column, list(values)))
        self.values = values
        return self

    def execute(self):
        return SimpleNamespace(
            data=[row for row in self.rows if row.get("document_key") in self.values]
        )


class _FakeSupabase:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[tuple] = []

    def table(self, table_name: str):
        self.calls.append(("table", table_name))
        return _FakeTableQuery(self, self.rows)


def _document_rows(major: str, *, las_content: str, major_content: str) -> list[dict]:
    return [
        {
            "document_key": MAJOR_DOCUMENT_KEYS[major],
            "content_markdown": major_content,
        },
        {
            "document_key": LAS_DOCUMENT_KEY,
            "content_markdown": las_content,
        },
    ]


class GraduationRequirementsToolTest(unittest.TestCase):
    def invoke_with_rows(self, major: str, rows: list[dict]):
        client = _FakeSupabase(rows)
        with patch(
            "tools.graduation_requirements_tool.create_supabase_client",
            return_value=client,
        ):
            result = get_graduation_requirements.invoke({"major": major})
        return result, client

    def test_math_returns_common_then_major_markdown_from_one_query(self) -> None:
        las = "# LAS Requirements\n\nLAS body\n"
        math = "# Mathematics, BSLAS\n\nMath body\n"
        result, client = self.invoke_with_rows(
            "math",
            _document_rows("math", las_content=las, major_content=math),
        )

        self.assertEqual(
            result,
            "# LAS COMMON REQUIREMENTS\n\n"
            f"{las}\n\n# MAJOR REQUIREMENTS\n\n{math}",
        )
        self.assertEqual(
            client.calls,
            [
                ("table", TABLE_NAME),
                ("select", "document_key,content_markdown"),
                (
                    "in",
                    "document_key",
                    [LAS_DOCUMENT_KEY, MAJOR_DOCUMENT_KEYS["math"]],
                ),
            ],
        )

    def test_stats_returns_exact_stored_markdown(self) -> None:
        las = "shared markdown"
        stats = "statistics markdown"
        result, _ = self.invoke_with_rows(
            "stats",
            _document_rows("stats", las_content=las, major_content=stats),
        )

        self.assertIn(las, result)
        self.assertIn(stats, result)
        self.assertLess(result.index(las), result.index(stats))
        self.assertNotIn(MAJOR_DOCUMENT_KEYS["math"], result)

    def test_input_only_accepts_math_or_stats(self) -> None:
        with self.assertRaises(ValidationError):
            get_graduation_requirements.invoke({"major": "cs"})

    def test_missing_or_empty_document_fails(self) -> None:
        cases = {
            "missing major": [
                {
                    "document_key": LAS_DOCUMENT_KEY,
                    "content_markdown": "LAS",
                }
            ],
            "empty LAS": _document_rows(
                "stats", las_content="  ", major_content="Statistics"
            ),
        }
        for name, rows in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    RuntimeError, "missing graduation requirement Markdown"
                ):
                    self.invoke_with_rows("stats", rows)

    def test_catalog_registers_graduation_requirements_tool(self) -> None:
        from nodes.catalog_lookup import CATALOG_SYSTEM_PROMPT, CATALOG_TOOLS

        self.assertIn(
            "get_graduation_requirements",
            {catalog_tool.name for catalog_tool in CATALOG_TOOLS},
        )
        self.assertIn("Always use get_graduation_requirements", CATALOG_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()

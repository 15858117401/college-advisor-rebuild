import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.course_instructor_gpa_tool import get_course_instructor_gpas


class _FakeQuery:
    def __init__(
        self,
        rows: list[dict],
        error: Exception | None = None,
    ) -> None:
        self.rows = rows
        self.error = error
        self.selected_fields: str | None = None
        self.filter_column: str | None = None
        self.filter_values: list[str] | None = None
        self.execute_calls = 0

    def select(self, fields: str):
        self.selected_fields = fields
        return self

    def in_(self, column: str, values: list[str]):
        self.filter_column = column
        self.filter_values = values
        return self

    def execute(self):
        self.execute_calls += 1
        if self.error is not None:
            raise self.error
        return SimpleNamespace(data=self.rows)


class _FakeSupabase:
    def __init__(self, query: _FakeQuery) -> None:
        self.query = query
        self.table_calls: list[str] = []

    def table(self, table_name: str) -> _FakeQuery:
        self.table_calls.append(table_name)
        return self.query


def _invoke_with_fake(
    course_codes: list[str],
    rows: list[dict],
    *,
    error: Exception | None = None,
):
    query = _FakeQuery(rows, error)
    client = _FakeSupabase(query)
    with patch(
        "tools.course_instructor_gpa_tool.create_supabase_client",
        return_value=client,
    ):
        result = get_course_instructor_gpas.invoke({"course_codes": course_codes})
    return result, client, query


class GetCourseInstructorGpasInputTest(unittest.TestCase):
    def test_rejects_empty_course_list(self) -> None:
        with self.assertRaises(ValidationError):
            get_course_instructor_gpas.invoke({"course_codes": []})

    def test_rejects_more_than_two_courses(self) -> None:
        with self.assertRaises(ValidationError):
            get_course_instructor_gpas.invoke(
                {"course_codes": ["STAT 100", "STAT 420", "STAT 425"]}
            )

    def test_rejects_non_stat_course_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected a value like 'STAT 420'"):
            get_course_instructor_gpas.invoke({"course_codes": ["CS 225"]})

    def test_normalizes_course_codes(self) -> None:
        result, _, query = _invoke_with_fake(
            ["stat420", " Stat   425 "],
            [],
        )

        self.assertEqual(query.filter_values, ["STAT 420", "STAT 425"])
        self.assertEqual(
            [course["course_code"] for course in result],
            ["STAT 420", "STAT 425"],
        )

    def test_tool_metadata_describes_limits_and_data_scope(self) -> None:
        course_codes = (
            get_course_instructor_gpas.args_schema.model_json_schema()["properties"]
            ["course_codes"]
        )

        self.assertEqual(course_codes["minItems"], 1)
        self.assertEqual(course_codes["maxItems"], 2)
        self.assertIn("not identify specific sections", get_course_instructor_gpas.description)


class GetCourseInstructorGpasQueryTest(unittest.TestCase):
    def test_queries_once_with_only_public_result_fields(self) -> None:
        rows = [
            {
                "course_code": "STAT 420",
                "instructor_name": "Unger, D.",
                "instructor_avg_gpa": 3.77,
            }
        ]

        result, client, query = _invoke_with_fake(
            ["stat420", "STAT 425"],
            rows,
        )

        self.assertEqual(client.table_calls, ["course_instructor_stats"])
        self.assertEqual(query.execute_calls, 1)
        self.assertEqual(query.filter_column, "course_code")
        self.assertEqual(query.filter_values, ["STAT 420", "STAT 425"])
        self.assertEqual(
            query.selected_fields,
            "course_code,instructor_name,instructor_avg_gpa",
        )
        self.assertEqual(
            result,
            [
                {
                    "course_code": "STAT 420",
                    "instructors": [
                        {"name": "Unger, D.", "average_gpa": 3.77}
                    ],
                },
                {
                    "course_code": "STAT 425",
                    "instructors": [],
                    "message": "no instructor GPA information",
                },
            ],
        )

    def test_averages_duplicate_instructors_and_sorts_results(self) -> None:
        rows = [
            {
                "course_code": "STAT 425",
                "instructor_name": "Simpson, D.",
                "instructor_avg_gpa": "3.62",
            },
            {
                "course_code": "STAT 425",
                "instructor_name": "Simpson, D.",
                "instructor_avg_gpa": "3.73",
            },
            {
                "course_code": "STAT 425",
                "instructor_name": "Bravo, L.",
                "instructor_avg_gpa": "3.675",
            },
            {
                "course_code": "STAT 425",
                "instructor_name": "Adams, A.",
                "instructor_avg_gpa": "3.675",
            },
            {
                "course_code": "STAT 425",
                "instructor_name": "Rounded, R.",
                "instructor_avg_gpa": "3.11",
            },
            {
                "course_code": "STAT 425",
                "instructor_name": "Rounded, R.",
                "instructor_avg_gpa": "3.12",
            },
            {
                "course_code": "STAT 425",
                "instructor_name": "Rounded, R.",
                "instructor_avg_gpa": "3.12",
            },
        ]

        result, _, _ = _invoke_with_fake(["STAT 425"], rows)

        self.assertEqual(
            result[0]["instructors"],
            [
                {"name": "Adams, A.", "average_gpa": 3.675},
                {"name": "Bravo, L.", "average_gpa": 3.675},
                {"name": "Simpson, D.", "average_gpa": 3.675},
                {"name": "Rounded, R.", "average_gpa": 3.117},
            ],
        )

    def test_ignores_null_gpas_and_returns_message_when_none_remain(self) -> None:
        rows = [
            {
                "course_code": "STAT 420",
                "instructor_name": "Known, K.",
                "instructor_avg_gpa": 3.5,
            },
            {
                "course_code": "STAT 420",
                "instructor_name": "Known, K.",
                "instructor_avg_gpa": None,
            },
            {
                "course_code": "STAT 361",
                "instructor_name": "Unknown, U.",
                "instructor_avg_gpa": None,
            },
        ]

        result, _, _ = _invoke_with_fake(["STAT 420", "STAT 361"], rows)

        self.assertEqual(
            result,
            [
                {
                    "course_code": "STAT 420",
                    "instructors": [
                        {"name": "Known, K.", "average_gpa": 3.5}
                    ],
                },
                {
                    "course_code": "STAT 361",
                    "instructors": [],
                    "message": "no instructor GPA information",
                },
            ],
        )

    def test_deduplicates_query_but_repeats_output(self) -> None:
        rows = [
            {
                "course_code": "STAT 420",
                "instructor_name": "Unger, D.",
                "instructor_avg_gpa": 3.82,
            }
        ]

        result, _, query = _invoke_with_fake(["STAT 420", "stat420"], rows)

        self.assertEqual(query.filter_values, ["STAT 420"])
        self.assertEqual(result[0], result[1])

    def test_propagates_supabase_failure(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            _invoke_with_fake(
                ["STAT 420"],
                [],
                error=RuntimeError("database unavailable"),
            )


class CatalogRegistrationTest(unittest.TestCase):
    def test_catalog_registers_instructor_gpa_tool(self) -> None:
        from nodes.catalog_lookup import CATALOG_SYSTEM_PROMPT, CATALOG_TOOLS

        self.assertIn(
            "get_course_instructor_gpas",
            {catalog_tool.name for catalog_tool in CATALOG_TOOLS},
        )
        self.assertIn("historical instructor GPA", CATALOG_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()

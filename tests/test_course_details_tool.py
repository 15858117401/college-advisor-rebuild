import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.course_details_tool import get_course_details


COURSE_ROW = {
    "course_code": "STAT 432",
    "subject": "STAT",
    "course_number": 432,
    "course_name": "Basics of Statistical Learning",
    "credits": "3 or 4 Hours",
    "description": "Topics in supervised and unsupervised learning.",
    "prerequisites": "STAT 400, and either STAT 420 or STAT 425.",
    "credit_restrictions": None,
    "gen_ed": None,
    "total_students": 1204,
    "total_sections": 18,
    "overall_gpa": 3.59,
}


class _FakeCourseQuery:
    def __init__(self, rows: list[dict], error: Exception | None = None) -> None:
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
    def __init__(self, query: _FakeCourseQuery) -> None:
        self.query = query
        self.table_calls: list[str] = []

    def table(self, table_name: str) -> _FakeCourseQuery:
        self.table_calls.append(table_name)
        return self.query


def _invoke_with_fake(
    course_codes: list[str],
    rows: list[dict],
    *,
    error: Exception | None = None,
):
    query = _FakeCourseQuery(rows, error)
    client = _FakeSupabase(query)
    with patch(
        "tools.course_details_tool.create_supabase_client",
        return_value=client,
    ):
        result = get_course_details.invoke({"course_codes": course_codes})
    return result, client, query


class GetCourseDetailsInputTest(unittest.TestCase):
    def test_rejects_empty_course_list(self) -> None:
        with self.assertRaises(ValidationError):
            get_course_details.invoke({"course_codes": []})

    def test_rejects_more_than_five_courses(self) -> None:
        with self.assertRaises(ValidationError):
            get_course_details.invoke(
                {
                    "course_codes": [
                        "STAT 100",
                        "STAT 107",
                        "STAT 200",
                        "STAT 207",
                        "STAT 212",
                        "STAT 400",
                    ]
                }
            )

    def test_rejects_non_stat_course_code(self) -> None:
        with self.assertRaisesRegex(ValidationError, "expected a value like 'STAT 107'"):
            get_course_details.invoke({"course_codes": ["CS 225"]})

    def test_tool_metadata_describes_exact_lookup_and_five_course_limit(self) -> None:
        self.assertIn("explicit course codes", get_course_details.description)
        self.assertIn("Do not use", get_course_details.description)
        course_codes = get_course_details.args_schema.model_json_schema()["properties"][
            "course_codes"
        ]
        self.assertEqual(course_codes["minItems"], 1)
        self.assertEqual(course_codes["maxItems"], 5)
        self.assertIn("STAT 432", course_codes["description"])


class GetCourseDetailsQueryTest(unittest.TestCase):
    def test_normalizes_codes_and_queries_once_without_internal_fields(self) -> None:
        result, client, query = _invoke_with_fake(
            [" stat 432 ", "Stat   400"],
            [COURSE_ROW],
        )

        self.assertEqual(client.table_calls, ["courses"])
        self.assertEqual(query.execute_calls, 1)
        self.assertEqual(query.filter_column, "course_code")
        self.assertEqual(query.filter_values, ["STAT 432", "STAT 400"])
        selected_fields = query.selected_fields.split(",")
        self.assertNotIn("id", selected_fields)
        self.assertNotIn("embedding", selected_fields)
        self.assertEqual(result[0], COURSE_ROW)
        self.assertEqual(
            result[1],
            {"course_code": "STAT 400", "message": "no such course"},
        )

    def test_returns_five_courses_in_input_order(self) -> None:
        codes = ["STAT 100", "STAT 107", "STAT 200", "STAT 400", "STAT 432"]
        rows = [
            {**COURSE_ROW, "course_code": code, "course_number": int(code[-3:])}
            for code in reversed(codes)
        ]

        result, _, query = _invoke_with_fake(codes, rows)

        self.assertEqual([row["course_code"] for row in result], codes)
        self.assertEqual(query.execute_calls, 1)

    def test_preserves_null_course_fields(self) -> None:
        row = {
            **COURSE_ROW,
            "prerequisites": None,
            "total_students": None,
            "total_sections": None,
            "overall_gpa": None,
        }

        result, _, _ = _invoke_with_fake(["STAT 432"], [row])

        self.assertIsNone(result[0]["prerequisites"])
        self.assertIsNone(result[0]["overall_gpa"])

    def test_deduplicates_query_but_repeats_output(self) -> None:
        result, _, query = _invoke_with_fake(
            ["STAT 432", "stat 432"],
            [COURSE_ROW],
        )

        self.assertEqual(query.filter_values, ["STAT 432"])
        self.assertEqual(result, [COURSE_ROW, COURSE_ROW])

    def test_propagates_supabase_failure(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            _invoke_with_fake(
                ["STAT 432"],
                [],
                error=RuntimeError("database unavailable"),
            )


if __name__ == "__main__":
    unittest.main()

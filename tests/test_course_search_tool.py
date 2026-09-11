import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.course_search_tool import (
    GEN_ED_CATEGORIES,
    FindCoursesInput,
    find_courses,
)


class _RpcRequest:
    def __init__(self, rows: list[dict], error: Exception | None = None) -> None:
        self.rows = rows
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.rows)


class _Client:
    def __init__(self, rows: list[dict], error: Exception | None = None) -> None:
        self.rows = rows
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name: str, params: dict):
        self.calls.append((name, params))
        return _RpcRequest(self.rows, self.error)


def _row(code: str, gpa: float | None, credits: str = "3 Hours") -> dict:
    return {
        "course_code": code,
        "credits": credits,
        "overall_gpa": gpa,
    }


def _invoke(
    payload: dict,
    rows: list[dict],
    *,
    database_error: Exception | None = None,
    embedding_error: Exception | None = None,
):
    client = _Client(rows, database_error)
    with (
        patch("tools.course_search_tool.create_supabase_client", return_value=client),
        patch(
            "tools.course_search_tool.embed_texts",
            return_value=[[1.0, 0.0]],
            side_effect=embedding_error,
        ) as embed_mock,
    ):
        result = find_courses.invoke(payload)
    return result, client, embed_mock


class FindCoursesTest(unittest.TestCase):
    def test_validates_conditions_and_ranges(self) -> None:
        invalid = [
            {},
            {"semantic_limit": 3},
            {"min_course_number": 500, "max_course_number": 400},
            {"min_overall_gpa": 3.5, "max_overall_gpa": 3.0},
            {"min_overall_gpa": -0.1},
            {"description_query": "   "},
            {"description_query": "models", "semantic_limit": 5},
            {"prerequisite_course": "STAT-400"},
            {"subjects": []},
            {"subjects": ["Math major"]},
            {"gen_ed": None},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                find_courses.invoke(payload)

    def test_gen_ed_schema_advertises_every_category_and_null(self) -> None:
        schema = FindCoursesInput.model_json_schema()["properties"]["gen_ed"]
        enum_schema = next(option for option in schema["anyOf"] if "enum" in option)
        null_schema = next(
            option for option in schema["anyOf"] if option.get("type") == "null"
        )

        self.assertEqual(enum_schema["enum"], GEN_ED_CATEGORIES)
        self.assertEqual(len(enum_schema["enum"]), 15)
        self.assertEqual(null_schema, {"type": "null"})

    def test_accepts_every_canonical_gen_ed_category(self) -> None:
        for category in GEN_ED_CATEGORIES:
            with self.subTest(category=category):
                self.assertEqual(FindCoursesInput(gen_ed=category).gen_ed, category)
        self.assertIsNone(
            FindCoursesInput(description_query="models", gen_ed=None).gen_ed
        )

    @patch("tools.course_search_tool.create_supabase_client")
    @patch("tools.course_search_tool.embed_texts")
    def test_rejects_noncanonical_gen_ed_before_dependencies(
        self,
        embed_mock,
        client_mock,
    ) -> None:
        for gen_ed in ["US Minority", "missing", "", "Unknown Category"]:
            with self.subTest(gen_ed=gen_ed), self.assertRaises(ValidationError):
                find_courses.invoke({"gen_ed": gen_ed})

        embed_mock.assert_not_called()
        client_mock.assert_not_called()

    def test_description_embeds_once_and_sends_every_filter_to_one_rpc(self) -> None:
        result, client, embed_mock = _invoke(
            {
                "description_query": "  race and citizenship  ",
                "subjects": [" aas ", "HIST", "AAS"],
                "min_course_number": 100,
                "max_course_number": 399,
                "credit_hours": 3,
                "gen_ed": " Cultural Studies - US Minority ",
                "prerequisite_course": "stat400",
                "min_overall_gpa": 3.0,
                "max_overall_gpa": 4.0,
            },
            [_row("AAS 215", 3.61)],
        )

        self.assertEqual(result, [{"course_code": "AAS 215", "credits": "3 Hours"}])
        embed_mock.assert_called_once_with(["race and citizenship"])
        self.assertEqual(len(client.calls), 1)
        name, params = client.calls[0]
        self.assertEqual(name, "search_courses")
        self.assertEqual(
            params,
            {
                "p_query_embedding": [1.0, 0.0],
                "p_subjects": ["AAS", "HIST"],
                "p_min_course_number": 100,
                "p_max_course_number": 399,
                "p_credit_hours": 3,
                "p_gen_ed": "Cultural Studies - US Minority",
                "p_prerequisite_course": "STAT 400",
                "p_min_overall_gpa": 3.0,
                "p_max_overall_gpa": 4.0,
            },
        )

    def test_structured_search_skips_embedding_and_uses_one_rpc(self) -> None:
        result, client, embed_mock = _invoke(
            {"gen_ed": "Cultural Studies - US Minority"},
            [_row("HIST 281", 3.59)],
        )

        embed_mock.assert_not_called()
        self.assertEqual(len(client.calls), 1)
        self.assertIsNone(client.calls[0][1]["p_query_embedding"])
        self.assertEqual(result[0]["course_code"], "HIST 281")

    def test_final_output_preserves_the_rpc_order_and_formats_fields(self) -> None:
        rows = [
            _row("AAS 215", 3.61),
            _row("AFRO 215", 3.61),
            _row("HIST 281", 3.59),
            _row("LLS 100", 3.53),
            _row("ZZZ 100", None),
        ]
        result, _, _ = _invoke({"min_course_number": 100}, rows)

        self.assertEqual(
            [row["course_code"] for row in result],
            ["AAS 215", "AFRO 215", "HIST 281", "LLS 100", "ZZZ 100"],
        )
        self.assertTrue(all(set(row) == {"course_code", "credits"} for row in result))

    def test_empty_result_is_a_normal_completed_query(self) -> None:
        result, client, embed_mock = _invoke(
            {
                "description_query": "unavailable topic",
                "gen_ed": "Cultural Studies - US Minority",
            },
            [],
        )
        self.assertEqual(result, [])
        embed_mock.assert_called_once()
        self.assertEqual(len(client.calls), 1)

    def test_upstream_failures_propagate(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            _invoke(
                {"min_course_number": 400},
                [],
                database_error=RuntimeError("database unavailable"),
            )
        with self.assertRaisesRegex(RuntimeError, "embedding unavailable"):
            _invoke(
                {"description_query": "models"},
                [],
                embedding_error=RuntimeError("embedding unavailable"),
            )


def _search_function(sql: str) -> str:
    start = sql.index("create function public.search_courses")
    end = sql.index("revoke all on function public.search_courses", start)
    return sql[start:end].replace("create function", "create or replace function", 1).strip()


def test_bootstrap_and_migration_have_the_same_search_function() -> None:
    bootstrap = (PROJECT_ROOT / "Supabase" / "stat_resource_schema.sql").read_text(
        encoding="utf-8"
    )
    migration = (PROJECT_ROOT / "Supabase" / "course_search_rpc_migration.sql").read_text(
        encoding="utf-8"
    )
    migration_function = migration[
        migration.index("create or replace function public.search_courses"):
        migration.index("revoke all on function public.search_courses")
    ].strip()
    assert _search_function(bootstrap) == migration_function


def test_sql_filters_before_semantic_top_five_then_orders_by_gpa() -> None:
    sql = (PROJECT_ROOT / "Supabase" / "course_search_rpc_migration.sql").read_text(
        encoding="utf-8"
    ).casefold()
    assert "course.subject = any (p_subjects)" in sql
    assert "regexp_split_to_table" in sql
    assert "lower(btrim(label.value)) = lower(btrim(p_gen_ed))" in sql
    assert "'(^|[^[:alnum:]])'" in sql
    assert "'([^[:alnum:]]|$)'" in sql
    assert "order by filtered.embedding <=> p_query_embedding" in sql
    assert sql.count("limit 5") == 2
    assert "order by selected.overall_gpa desc nulls last" in sql
    assert "selected.course_code" in sql
    assert "security invoker" in sql


def test_python_delegates_searching_and_sorting_to_the_rpc() -> None:
    source = (PROJECT_ROOT / "tools" / "course_search_tool.py").read_text(
        encoding="utf-8"
    )
    assert "fetch_all_rows" not in source
    assert '.table("courses")' not in source
    assert 'row["embedding"]' not in source
    assert "sorted(" not in source


if __name__ == "__main__":
    unittest.main()

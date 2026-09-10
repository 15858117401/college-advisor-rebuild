import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.course_search_tool import find_courses


def _row(
    code: str,
    *,
    credits: str = "3 Hours",
    prerequisites: str | None = None,
    gen_ed: str | None = None,
    gpa: float | None = 3.5,
    embedding=None,
) -> dict:
    result = {
        "course_code": code,
        "course_number": int(code.split()[1]),
        "credits": credits,
        "prerequisites": prerequisites,
        "gen_ed": gen_ed,
        "overall_gpa": gpa,
    }
    if embedding is not None:
        result["embedding"] = embedding
    return result


class _Query:
    def __init__(self, rows: list[dict], error: Exception | None = None) -> None:
        self.rows = rows
        self.error = error

    def select(self, fields: str):
        return self

    def eq(self, column: str, value):
        return self

    def in_(self, column, values):
        self.rows = [row for row in self.rows if row['course_code'].split()[0] in values]
        return self

    def order(self, column):
        self.rows = sorted(self.rows, key=lambda row: row[column])
        return self

    def range(self, start, end):
        self.page = self.rows[start:end + 1]
        return self

    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.page)


def _invoke(
    payload: dict,
    rows: list[dict],
    *,
    database_error: Exception | None = None,
    embedding_error: Exception | None = None,
):
    query = _Query(rows, database_error)
    with (
        patch(
            "tools.course_search_tool.create_supabase_client",
            return_value=SimpleNamespace(table=lambda name: query),
        ),
        patch(
            "tools.course_search_tool.embed_texts",
            return_value=[[1.0, 0.0]],
            side_effect=embedding_error,
        ) as embed_mock,
    ):
        result = find_courses.invoke(payload)
    return result, embed_mock


class FindCoursesTest(unittest.TestCase):
    def test_validates_conditions_and_ranges(self) -> None:
        invalid = [
            {},
            {"semantic_limit": 3},
            {"min_course_number": 500, "max_course_number": 400},
            {"min_overall_gpa": 3.5, "max_overall_gpa": 3.0},
            {"min_overall_gpa": -0.1},
            {"description_query": "models", "semantic_limit": 21},
            {"prerequisite_course": "STAT-400"},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                find_courses.invoke(payload)

    def test_combines_structured_rules_with_and(self) -> None:
        rows = [
            _row(
                "STAT 207",
                credits="4 Hours",
                prerequisites="STAT 107.",
                gen_ed="Quantitative Reasoning II",
                gpa=3.6,
            ),
            _row("STAT 212", credits="3 Hours", gen_ed="Quantitative Reasoning I"),
            _row("STAT 425", credits="3 or 4 Hours", prerequisites="STAT 400."),
        ]
        result, embed_mock = _invoke(
            {
                "min_course_number": 200,
                "max_course_number": 499,
                "credit_hours": 4,
                "gen_ed": "Quantitative Reasoning II",
                "prerequisite_course": "stat107",
                "min_overall_gpa": 3.55,
            },
            rows,
        )
        self.assertEqual(result, [{"course_code": "STAT 207", "credits": "4 Hours"}])
        embed_mock.assert_not_called()

    def test_prerequisite_course_matches_exact_codes_in_compound_text(self) -> None:
        rows = [
            _row("STAT 410", prerequisites="MATH 241 and STAT 400."),
            _row("STAT 432", prerequisites="STAT 400A or STAT 425."),
            _row("STAT 440", prerequisites=None),
        ]

        result, embed_mock = _invoke(
            {"prerequisite_course": "stat400"},
            rows,
        )

        self.assertEqual([item["course_code"] for item in result], ["STAT 410"])
        embed_mock.assert_not_called()

    def test_missing_gpa_does_not_satisfy_gpa_filter(self) -> None:
        result, _ = _invoke(
            {"min_overall_gpa": 3.5},
            [_row("STAT 408", gpa=3.09), _row("STAT 429", gpa=None)],
        )
        self.assertEqual(result, [])

    def test_credit_filter_supports_fixed_optional_and_range_values(self) -> None:
        rows = [
            _row("STAT 100", credits="3 Hours"),
            _row("STAT 400", credits="4 Hours"),
            _row("STAT 432", credits="3 or 4 Hours"),
            _row("STAT 590", credits="0 to 8 Hours"),
        ]
        result, _ = _invoke({"credit_hours": 3}, rows)
        self.assertEqual(
            [item["course_code"] for item in result],
            ["STAT 100", "STAT 432", "STAT 590"],
        )

    def test_without_query_returns_all_matches_in_course_number_order(self) -> None:
        result, _ = _invoke(
            {"min_course_number": 100},
            [
                _row("STAT 432", credits="3 or 4 Hours"),
                _row("STAT 107", credits="4 Hours"),
                _row("STAT 400", credits="4 Hours"),
            ],
        )
        self.assertEqual(
            [item["course_code"] for item in result],
            ["STAT 107", "STAT 400", "STAT 432"],
        )
        self.assertTrue(all(set(item) == {"course_code", "credits"} for item in result))

    def test_rules_run_before_semantic_top_k(self) -> None:
        rows = [_row("STAT 100", embedding=json.dumps([1.0, 0.0]))]
        rows += [
            _row(f"STAT {number}", embedding=json.dumps([1.0, offset * 0.1]))
            for offset, number in enumerate(range(400, 407))
        ]
        result, embed_mock = _invoke(
            {"description_query": "models", "min_course_number": 400}, rows
        )
        self.assertEqual(
            [item["course_code"] for item in result],
            ["STAT 400", "STAT 401", "STAT 402", "STAT 403", "STAT 404"],
        )
        embed_mock.assert_called_once_with(["models"])

        limited, _ = _invoke(
            {
                "description_query": "models",
                "min_course_number": 400,
                "semantic_limit": 2,
            },
            rows,
        )
        self.assertEqual([item["course_code"] for item in limited], ["STAT 400", "STAT 401"])

    def test_empty_candidates_skip_embedding(self) -> None:
        result, embed_mock = _invoke(
            {"description_query": "models", "min_course_number": 500},
            [_row("STAT 107", embedding=[1.0, 0.0])],
        )
        self.assertEqual(result, [])
        embed_mock.assert_not_called()

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
                [_row("STAT 432", embedding=[1.0, 0.0])],
                embedding_error=RuntimeError("embedding unavailable"),
            )




def test_cross_subject_search_and_normalized_filter():
    rows = [_row('MATH 416'), _row('ECON 302'), _row('STAT 400')]
    result, _ = _invoke({'min_course_number': 100}, rows)
    assert len(result) == 3
    result, _ = _invoke({'subjects': [' econ ', 'MATH', 'ECON']}, rows)
    assert {r['course_code'] for r in result} == {'ECON 302', 'MATH 416'}


def test_reads_past_1000_rows():
    rows = [_row(f'{subject} {n}') for subject in ['MATH', 'ECON'] for n in range(100, 700)]
    result, _ = _invoke({'min_course_number': 100}, rows)
    assert len(result) == 1200
    assert len({r['course_code'] for r in result}) == 1200


def test_null_embedding_is_factual_only():
    rows = [_row('CWL 593', embedding=None), _row('CWL 590', embedding=[1.0, 0.0])]
    result, _ = _invoke({'min_course_number': 500}, rows)
    assert len(result) == 2
    result, _ = _invoke({'description_query': 'literature'}, rows)
    assert [r['course_code'] for r in result] == ['CWL 590']
    result, embed = _invoke({'description_query': 'literature'}, rows[:1])
    assert result == []
    embed.assert_not_called()


def test_general_education_matches_one_of_multiple_labels():
    rows = [_row('HIST 100', gen_ed='Humanities - Hist & Phil\nCultural Studies - Western'),
            _row('ECON 102', gen_ed='Social & Beh Sci - Soc Sci')]
    result, _ = _invoke({'gen_ed': 'cultural studies - western'}, rows)
    assert [r['course_code'] for r in result] == ['HIST 100']


def test_unknown_gpa_neither_minimum_nor_maximum():
    for criteria in [{'min_overall_gpa': 2}, {'max_overall_gpa': 4}]:
        result, _ = _invoke(criteria, [_row('ECON 302', gpa=None)])
        assert result == []


def test_invalid_subject_filters():
    for subjects in [[], ['Math major'], ['ECON;DELETE']]:
        with pytest.raises(ValidationError):
            find_courses.invoke({'subjects': subjects})


if __name__ == "__main__":
    unittest.main()

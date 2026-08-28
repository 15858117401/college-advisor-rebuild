import csv
import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from client.embedding_client import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, embed_texts
from tools.import_stat_resources import (
    INSTRUCTORS_CSV,
    EXPECTED_PROJECT_REF,
    load_resource_data,
    upload_snapshot,
    validate_supabase_url,
    validation_summary,
)


class _FakeEmbeddings:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=index, embedding=vector)
                for index, vector in enumerate(self.vectors)
            ]
        )


class _FakeOpenAI:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.embeddings = _FakeEmbeddings(vectors)


class _FakeRpcRequest:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return SimpleNamespace(data=self.data)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        if name == "replace_stat_resource_snapshot":
            return _FakeRpcRequest(
                [{"courses_upserted": 41, "instructor_rows_inserted": 117}]
            )
        if name == "match_courses":
            return _FakeRpcRequest(
                [{"course_code": "STAT 100", "similarity": 1.0}]
            )
        raise AssertionError(f"unexpected RPC {name}")


class EmbeddingClientTest(unittest.TestCase):
    def test_embeds_with_fixed_model_and_dimensions(self) -> None:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        client = _FakeOpenAI([vector])

        result = embed_texts(["course description"], client=client)

        self.assertEqual(result, [vector])
        self.assertEqual(client.embeddings.request["model"], EMBEDDING_MODEL)
        self.assertEqual(
            client.embeddings.request["dimensions"], EMBEDDING_DIMENSIONS
        )
        self.assertEqual(client.embeddings.request["input"], ["course description"])

    def test_rejects_empty_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            embed_texts(["  "], client=_FakeOpenAI([]))

    def test_rejects_wrong_vector_size(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "expected 1536 dimensions"):
            embed_texts(["text"], client=_FakeOpenAI([[0.0]]))

    def test_rejects_non_finite_vector(self) -> None:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        vector[10] = math.nan
        with self.assertRaisesRegex(RuntimeError, "non-finite"):
            embed_texts(["text"], client=_FakeOpenAI([vector]))


class ResourceImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_resource_data()

    def test_resource_snapshot_is_valid(self) -> None:
        summary = validation_summary(self.data)

        self.assertEqual(summary["courses"], 41)
        self.assertEqual(summary["instructor_rows"], 117)
        self.assertEqual(summary["courses_without_gpa"], 19)
        self.assertEqual(
            summary["stat_100"],
            {
                "course_name": "Statistics",
                "total_students": 12977,
                "total_sections": 28,
                "overall_gpa": 3.28,
            },
        )

    def test_optional_csv_values_become_none(self) -> None:
        self.assertTrue(any(course["overall_gpa"] is None for course in self.data.courses))
        self.assertTrue(
            any(
                row["gpa_delta_from_course"] is None
                for row in self.data.instructors
            )
        )

    def test_instructor_course_identifiers_match_courses(self) -> None:
        courses_by_code = {
            course["course_code"]: course for course in self.data.courses
        }

        for instructor in self.data.instructors:
            course = courses_by_code[instructor["course_code"]]
            self.assertEqual(instructor["subject"], course["subject"])
            self.assertEqual(instructor["course_number"], course["course_number"])

    def test_rejects_inconsistent_instructor_course_identifiers(self) -> None:
        with INSTRUCTORS_CSV.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        fieldnames = list(rows[0])

        invalid_values = {
            "course_code": "STAT 107",
            "subject": "CS",
            "course_number": "107",
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                invalid_rows = [dict(row) for row in rows]
                invalid_rows[0][field] = value
                invalid_path = Path(directory) / INSTRUCTORS_CSV.name
                with invalid_path.open("w", encoding="utf-8", newline="") as target:
                    writer = csv.DictWriter(target, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(invalid_rows)

                with self.assertRaisesRegex(
                    ValueError, "inconsistent course identifiers"
                ):
                    load_resource_data(instructors_path=invalid_path)

    def test_same_teacher_with_different_stats_is_preserved(self) -> None:
        unger = [
            row
            for row in self.data.instructors
            if row["course_code"] == "STAT 420"
            and row["instructor_name"] == "Unger, D."
        ]
        self.assertEqual(len(unger), 2)
        self.assertNotEqual(unger[0]["instructor_avg_gpa"], unger[1]["instructor_avg_gpa"])

    def test_rejects_wrong_supabase_project(self) -> None:
        with self.assertRaisesRegex(RuntimeError, EXPECTED_PROJECT_REF):
            validate_supabase_url("https://wrong-project.supabase.co")

    def test_builds_atomic_import_and_checks_semantic_search(self) -> None:
        client = _FakeSupabase()
        vectors = [[0.0] * EMBEDDING_DIMENSIONS for _ in self.data.courses]

        result = upload_snapshot(self.data, vectors, supabase_client=client)

        self.assertEqual(result["courses"], 41)
        self.assertEqual(result["instructor_rows"], 117)
        self.assertEqual(result["semantic_search_top_match"], "STAT 100")
        self.assertEqual(client.calls[0][0], "replace_stat_resource_snapshot")
        self.assertEqual(len(client.calls[0][1]["course_rows"]), 41)
        self.assertEqual(len(client.calls[0][1]["instructor_rows"]), 117)
        self.assertEqual(
            {
                key: client.calls[0][1]["instructor_rows"][0][key]
                for key in ("course_code", "subject", "course_number")
            },
            {
                "course_code": "STAT 100",
                "subject": "STAT",
                "course_number": 100,
            },
        )
        self.assertEqual(client.calls[1][0], "match_courses")


if __name__ == "__main__":
    unittest.main()

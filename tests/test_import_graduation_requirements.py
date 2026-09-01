import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Supabase.import_graduation_requirements import (
    EXPECTED_DOCUMENT_KEYS,
    MANIFEST_PATH,
    TABLE_NAME,
    load_requirement_documents,
    upload_documents,
    validation_summary,
)


class _FakeTableQuery:
    def __init__(self, client, table_name: str) -> None:
        self.client = client
        self.table_name = table_name
        self.operation = None
        self.payload = None
        self.on_conflict = None
        self.selected_fields = None
        self.filter_column = None
        self.filter_values = None

    def upsert(self, rows, *, on_conflict: str):
        self.operation = "upsert"
        self.payload = [dict(row) for row in rows]
        self.on_conflict = on_conflict
        return self

    def select(self, fields: str):
        self.operation = "select"
        self.selected_fields = fields
        return self

    def in_(self, column: str, values: list[str]):
        self.filter_column = column
        self.filter_values = list(values)
        return self

    def execute(self):
        if self.operation == "upsert":
            self.client.calls.append(
                (
                    "upsert",
                    self.table_name,
                    self.on_conflict,
                    [dict(row) for row in self.payload],
                )
            )
            for row in self.payload:
                self.client.rows[row["document_key"]] = dict(row)
            return SimpleNamespace(data=[dict(row) for row in self.payload])

        if self.operation == "select":
            self.client.calls.append(
                (
                    "select",
                    self.table_name,
                    self.selected_fields,
                    self.filter_column,
                    list(self.filter_values),
                )
            )
            fields = self.selected_fields.split(",")
            rows = [
                {field: self.client.rows[key][field] for field in fields}
                for key in self.filter_values
                if key in self.client.rows
            ]
            if self.client.corrupt_content and rows:
                rows[0]["content_markdown"] += "corrupted"
            return SimpleNamespace(data=rows)

        raise AssertionError("query has no operation")


class _FakeSupabase:
    def __init__(self, *, corrupt_content: bool = False) -> None:
        self.rows = {}
        self.calls = []
        self.corrupt_content = corrupt_content

    def table(self, table_name: str):
        return _FakeTableQuery(self, table_name)


class GraduationRequirementResourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = load_requirement_documents()
        cls.by_key = {
            document.document_key: document for document in cls.documents
        }

    def test_snapshot_has_only_two_program_documents(self) -> None:
        self.assertEqual(
            validation_summary(self.documents),
            {
                "documents": 2,
                "shared_documents": 0,
                "program_documents": 2,
                "document_keys": sorted(EXPECTED_DOCUMENT_KEYS),
            },
        )

        for document in self.documents:
            self.assertEqual(document.document_type, "program")
            self.assertIsNone(document.parent_document_key)
            self.assertNotIn("college_code", document.database_row())

    def test_mathematics_document_has_required_spot_checks(self) -> None:
        content = self.by_key[
            "UIUC-MATH-BSLAS-2026-2027"
        ].content_markdown

        self.assertIn("### Approved Supporting Coursework — 12 hours", content)
        self.assertIn("### Analysis Requirement — 3 hours", content)
        self.assertIn("### Breadth Requirement — 6 hours", content)
        self.assertIn("optional concentration", content)
        for course_code in (
            "MATH 402",
            "MATH 403",
            "MATH 423",
            "MATH 441",
            "MATH 446",
            "MATH 448",
            "MATH 453",
            "MATH 481",
        ):
            self.assertIn(course_code, content)

    def test_statistics_document_preserves_both_hour_totals_and_choices(self) -> None:
        content = self.by_key[
            "UIUC-STAT-BSLAS-2026-2027"
        ].content_markdown

        self.assertIn("**70–72 hours**", content)
        self.assertIn("**42–44 total hours**", content)
        self.assertIn("Calculus through MATH 241", content)
        self.assertIn("MATH 220 — Calculus, or MATH 221", content)
        self.assertIn("MATH 231 — Calculus II", content)
        self.assertIn("MATH 241 — Calculus III", content)
        self.assertEqual(content.count("Select one:"), 2)
        self.assertIn("Select four courses from the following list:", content)
        for course_code in (
            "STAT 385",
            "STAT 424",
            "STAT 427",
            "STAT 428",
            "STAT 429",
            "STAT 430",
            "STAT 431",
            "STAT 432",
            "STAT 433",
            "STAT 434",
            "STAT 440",
            "STAT 443",
            "STAT 447",
            "STAT 448",
            "STAT 480",
            "MATH 444",
            "MATH 447",
        ):
            self.assertIn(course_code, content)

    def test_program_documents_exclude_general_education_content(self) -> None:
        for document in self.documents:
            content = document.content_markdown
            self.assertNotIn("General Education", content)
            self.assertNotIn("LAS BSLAS common requirements", content)
            self.assertNotIn("## Language Other Than English", content)
            self.assertNotIn("| Composition I |", content)

    def test_rejects_duplicate_manifest_document_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_dir = Path(directory)
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            manifest["documents"][1]["document_key"] = manifest["documents"][0][
                "document_key"
            ]
            for document in manifest["documents"]:
                shutil.copy(
                    MANIFEST_PATH.parent / document["file_name"],
                    temp_dir / document["file_name"],
                )
            temp_manifest = temp_dir / "manifest.json"
            temp_manifest.write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "duplicate document_key"):
                load_requirement_documents(temp_manifest)


class GraduationRequirementUploadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = load_requirement_documents()

    def test_uploads_program_documents_and_verifies_exact_markdown(self) -> None:
        client = _FakeSupabase()

        result = upload_documents(self.documents, supabase_client=client)

        self.assertEqual(
            result,
            {
                "documents": 2,
                "document_keys": sorted(EXPECTED_DOCUMENT_KEYS),
                "content_verified": True,
            },
        )
        self.assertEqual(client.calls[0][0:3], ("upsert", TABLE_NAME, "document_key"))
        self.assertEqual(
            {row["document_type"] for row in client.calls[0][3]}, {"program"}
        )
        self.assertTrue(
            all("college_code" not in row for row in client.calls[0][3])
        )
        self.assertEqual(client.calls[1][0], "select")
        for document in self.documents:
            self.assertEqual(
                client.rows[document.document_key]["content_markdown"],
                document.content_markdown,
            )

    def test_repeated_upload_remains_two_rows(self) -> None:
        client = _FakeSupabase()

        upload_documents(self.documents, supabase_client=client)
        upload_documents(self.documents, supabase_client=client)

        self.assertEqual(set(client.rows), EXPECTED_DOCUMENT_KEYS)
        self.assertEqual(len(client.rows), 2)

    def test_rejects_markdown_changed_after_upload(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "stored Markdown does not match"):
            upload_documents(
                self.documents,
                supabase_client=_FakeSupabase(corrupt_content=True),
            )


class GraduationRequirementSchemaTest(unittest.TestCase):
    def test_schema_uses_text_storage_and_service_role_access(self) -> None:
        schema = (
            PROJECT_ROOT / "Supabase" / "graduation_requirements_schema.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("content_markdown text not null", schema)
        self.assertIn("parent_document_key text", schema)
        self.assertNotIn("college_code", schema)
        self.assertNotIn("graduation_requirement_shared_version_idx", schema)
        self.assertIn(
            "create or replace function public.touch_graduation_requirement_document_updated_at()",
            schema,
        )
        self.assertIn("enable row level security", schema)
        self.assertIn("to service_role", schema)
        self.assertNotIn("embedding", schema)
        self.assertNotIn("jsonb", schema)

    def test_migration_removes_shared_document_and_college_code(self) -> None:
        migration = (
            PROJECT_ROOT
            / "Supabase"
            / "major_only_graduation_requirements_migration.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("set parent_document_key = null", migration)
        self.assertIn(
            "where document_key = 'UIUC-LAS-BSLAS-2026-2027'", migration
        )
        self.assertIn("drop column if exists college_code", migration)
        self.assertIn("check (document_type = 'program')", migration)


if __name__ == "__main__":
    unittest.main()

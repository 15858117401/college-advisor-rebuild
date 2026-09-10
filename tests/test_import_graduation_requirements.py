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
    validation_summary,
)


class GraduationRequirementResourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = load_requirement_documents()
        cls.by_key = {
            document.document_key: document for document in cls.documents
        }

    def test_snapshot_has_all_61_documents(self) -> None:
        self.assertEqual(len(self.documents), 61)
        self.assertTrue(EXPECTED_DOCUMENT_KEYS <= set(self.by_key))
        self.assertEqual(sum(d.document_type == "program" for d in self.documents), 60)
        biology = self.by_key["UIUC-BIOLOGY-REDIRECT-2026-2027"]
        self.assertEqual(biology.document_type, "program_redirect")
        self.assertIsNone(biology.degree_code)
        for document in self.documents:
            self.assertEqual(document.content_markdown.encode("utf-8"),
                             (MANIFEST_PATH.parent / document.file_name).read_bytes())
            self.assertIsNone(document.parent_document_key)

    def test_mathematics_document_has_required_spot_checks(self) -> None:
        content = self.by_key[
            "UIUC-MATH-BSLAS-2026-2027"
        ].content_markdown

        self.assertIn("### Supporting coursework outside Mathematics — 12 hours", content)
        self.assertIn("### Analysis — 3 hours", content)
        self.assertIn("### Breadth — 6 hours", content)
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

        self.assertIn("70–72 hours", content)
        self.assertIn("42–44 hours", content)
        self.assertIn("Calculus through MATH 241", content)
        self.assertIn("Choose one introductory statistics course", content)
        self.assertIn("Choose one linear algebra course", content)
        self.assertIn("Choose four courses from the following options.", content)
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
        for key in EXPECTED_DOCUMENT_KEYS:
            content = self.by_key[key].content_markdown
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

import sys
import unittest
from pathlib import Path

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from profile.markdown import render_degree_audit_markdown, render_snapshot_json
from profile.schema import (
    COURSE_FLAG_MEANINGS,
    FLAG_CLASSIFICATIONS,
    CourseAttempt,
    DegreeAuditSnapshot,
    KnownCourseFlag,
    degree_audit_json_schema,
    snapshot_from_json,
    snapshot_to_json,
)


def synthetic_snapshot_payload(
    *,
    major: str = "Statistics",
    concentration: str | None = None,
) -> dict:
    return {
        "schema_version": "1.0.0",
        "snapshot_id": "snapshot-synthetic",
        "source": {
            "sha256": "a" * 64,
            "page_count": 4,
            "parser_name": "synthetic-fixture",
            "parser_version": "1.0.0",
        },
        "audit": {
            "as_of_date": "2030-01-15",
            "prepared_on": "2030-01-16",
            "catalog_year": "2029-2030",
            "expected_graduation_date": "2031-05-15",
            "program": {
                "institution": "Example University",
                "college": "College of Examples",
                "degree": "Bachelor of Science",
                "major": major,
                "program_name": f"Synthetic {major} Program",
                "program_code": "EXAMPLE-BS-001",
                "concentration": concentration,
            },
        },
        "summary": {
            "source_status": "IP",
            "status": "in_progress",
            "credit_hours": {
                "required": 120,
                "earned": 72,
                "in_progress": 6,
                "remaining": 42,
            },
            "gpas": [
                {
                    "metric_id": "cumulative-gpa",
                    "label": "Cumulative GPA",
                    "value": 3.25,
                    "minimum_required": 2,
                }
            ],
            "measurements": [
                {
                    "measurement_id": "advanced-hours",
                    "label": "Advanced hours earned",
                    "value": 18,
                    "unit": "credit hours",
                }
            ],
        },
        "requirements": [
            {
                "requirement_id": "req-program",
                "position": 0,
                "code": "PROGRAM",
                "title": "Program requirements",
                "source_status": "IP",
                "status": "in_progress",
                "explanation": "Complete the program requirements below.",
                "credit_hours": {"required": 50, "earned": 30, "remaining": 20},
                "source_references": [{"page": 1, "line": 20}],
            },
            {
                "requirement_id": "req-core",
                "parent_requirement_id": "req-program",
                "position": 0,
                "title": "Synthetic core",
                "source_status": "OK",
                "status": "satisfied",
                "rules": [
                    {
                        "rule_id": "rule-core-hours",
                        "rule_type": "minimum_hours",
                        "description": "Complete the synthetic core.",
                        "required_value": 3,
                        "unit": "credit hours",
                    }
                ],
            },
            {
                "requirement_id": "req-choice",
                "parent_requirement_id": "req-program",
                "position": 1,
                "title": "Synthetic sequence choice",
                "source_status": "NO",
                "status": "unsatisfied",
                "rules": [
                    {
                        "rule_id": "rule-select",
                        "rule_type": "select_from",
                        "description": "Select one synthetic sequence.",
                        "required_value": 1,
                        "unit": "course",
                        "options": ["SYN 201", "SYN 202"],
                    }
                ],
                "notes": ["Either listed option may satisfy this requirement."],
            },
        ],
        "course_attempts": [
            {
                "attempt_id": "attempt-completed",
                "term": {"code": "FA", "year": 2029, "label": "Fall 2029"},
                "subject": "SYN",
                "number": "101",
                "title": "Synthetic Foundations",
                "grade": "A",
                "credits": {"attempted": 3, "earned": 3},
                "source_type": "uiuc",
                "classifications": ["completed"],
                "source_references": [{"page": 2, "bbox": [10, 20, 100, 30]}],
            },
            {
                "attempt_id": "attempt-progress",
                "term": {"code": "SP", "year": 2030, "label": "Spring 2030"},
                "subject": "SYN",
                "number": "201",
                "title": "Synthetic Modeling",
                "grade": "IP",
                "credits": {"attempted": 3},
                "source_type": "uiuc",
                "flags": [">I"],
                "classifications": ["in_progress"],
            },
            {
                "attempt_id": "attempt-duplicate",
                "term": {"code": "FA", "year": 2028, "label": "Fall 2028"},
                "subject": "SYN",
                "number": "099",
                "title": "Synthetic Duplicate Record",
                "grade": "B",
                "credits": {"attempted": 3, "earned": 0},
                "source_type": "uiuc",
                "flags": [">D", ">X"],
                "unknown_flags": [">Z"],
                "classifications": ["duplicate", "excluded"],
            },
        ],
        "course_applications": [
            {
                "application_id": "application-program",
                "requirement_id": "req-program",
                "attempt_id": "attempt-completed",
                "position": 0,
                "applied_credits": 3,
            },
            {
                "application_id": "application-core",
                "requirement_id": "req-core",
                "attempt_id": "attempt-completed",
                "position": 0,
                "applied_credits": 3,
                "notes": ["Applied to the core."],
            },
            {
                "application_id": "application-choice",
                "requirement_id": "req-choice",
                "attempt_id": "attempt-progress",
                "position": 0,
                "applied_credits": 3,
            },
        ],
        "warnings": [
            {
                "warning_id": "warning-unknown-flag",
                "code": "UNKNOWN_FLAG",
                "severity": "warning",
                "message": "An unrecognized course flag was preserved for review.",
                "attempt_id": "attempt-duplicate",
                "source_references": [{"page": 3, "line": 12}],
            }
        ],
    }


class DegreeAuditSchemaTest(unittest.TestCase):
    def test_profile_package_preserves_standard_cprofile_import(self) -> None:
        import cProfile

        self.assertTrue(callable(cProfile.run))
        self.assertTrue(hasattr(cProfile, "Profile"))

    def test_json_round_trip_is_valid_and_deterministic(self) -> None:
        snapshot = DegreeAuditSnapshot.model_validate(synthetic_snapshot_payload())

        serialized = snapshot_to_json(snapshot)
        restored = snapshot_from_json(serialized)

        self.assertEqual(restored, snapshot)
        self.assertEqual(snapshot_to_json(restored), serialized)
        self.assertTrue(serialized.endswith("\n"))

    def test_exports_portable_json_schema_for_local_storage(self) -> None:
        json_schema = degree_audit_json_schema()

        self.assertEqual(json_schema["title"], "DegreeAuditSnapshot")
        self.assertTrue(
            {
                "snapshot_id",
                "source",
                "audit",
                "summary",
                "requirements",
                "course_attempts",
                "course_applications",
                "warnings",
            }.issubset(json_schema["properties"])
        )

    def test_rejects_unknown_fields_and_invalid_status_mapping(self) -> None:
        unknown_field = synthetic_snapshot_payload()
        unknown_field["unexpected"] = "not allowed"
        with self.assertRaises(ValidationError):
            DegreeAuditSnapshot.model_validate(unknown_field)

        invalid_status = synthetic_snapshot_payload()
        invalid_status["requirements"][0]["status"] = "satisfied"
        with self.assertRaisesRegex(ValidationError, "must normalize to"):
            DegreeAuditSnapshot.model_validate(invalid_status)

    def test_requirement_tree_rejects_cycles_and_unknown_links(self) -> None:
        cyclic = synthetic_snapshot_payload()
        cyclic["requirements"][0]["parent_requirement_id"] = "req-core"
        with self.assertRaisesRegex(ValidationError, "must not contain cycles"):
            DegreeAuditSnapshot.model_validate(cyclic)

        unknown_attempt = synthetic_snapshot_payload()
        unknown_attempt["course_applications"][0]["attempt_id"] = "missing"
        with self.assertRaisesRegex(ValidationError, "unknown attempt"):
            DegreeAuditSnapshot.model_validate(unknown_attempt)

    def test_one_attempt_can_apply_to_multiple_requirements(self) -> None:
        snapshot = DegreeAuditSnapshot.model_validate(synthetic_snapshot_payload())

        completed_links = [
            application
            for application in snapshot.course_applications
            if application.attempt_id == "attempt-completed"
        ]

        self.assertEqual(len(snapshot.course_attempts), 3)
        self.assertEqual(len(completed_links), 2)
        self.assertEqual(
            {application.requirement_id for application in completed_links},
            {"req-program", "req-core"},
        )

    def test_every_known_flag_has_meaning_and_requires_classification(self) -> None:
        self.assertEqual(set(COURSE_FLAG_MEANINGS), set(KnownCourseFlag))
        self.assertEqual(set(FLAG_CLASSIFICATIONS), set(KnownCourseFlag))

        for flag in KnownCourseFlag:
            with self.subTest(flag=flag.value):
                expected = FLAG_CLASSIFICATIONS[flag]
                attempt = CourseAttempt.model_validate(
                    {
                        "attempt_id": f"flag-{flag.name.lower()}",
                        "subject": "SYN",
                        "number": "999",
                        "flags": [flag.value],
                        "classifications": [expected.value],
                    }
                )
                self.assertEqual(attempt.flags, (flag,))

                with self.assertRaisesRegex(
                    ValidationError,
                    "requires classification",
                ):
                    CourseAttempt.model_validate(
                        {
                            "attempt_id": f"invalid-{flag.name.lower()}",
                            "subject": "SYN",
                            "number": "999",
                            "flags": [flag.value],
                            "classifications": ["unknown"],
                        }
                    )

    def test_new_major_and_concentration_require_no_schema_change(self) -> None:
        payload = synthetic_snapshot_payload(
            major="Computational Botany",
            concentration="Forest Algorithms",
        )

        snapshot = DegreeAuditSnapshot.model_validate(payload)

        self.assertEqual(snapshot.audit.program.major, "Computational Botany")
        self.assertEqual(snapshot.audit.program.concentration, "Forest Algorithms")

    def test_applied_mathematics_shape_supports_multiple_selection_rules(self) -> None:
        payload = synthetic_snapshot_payload(
            major="Mathematics",
            concentration="Applied Mathematics",
        )
        payload["requirements"][2]["rules"].append(
            {
                "rule_id": "rule-second-select",
                "rule_type": "select_from",
                "description": "Select one additional modeling course.",
                "required_value": 1,
                "unit": "course",
                "options": ["SYN 301", "SYN 302", "SYN 303"],
            }
        )

        snapshot = DegreeAuditSnapshot.model_validate(payload)
        markdown = render_degree_audit_markdown(snapshot)

        self.assertEqual(snapshot.audit.program.major, "Mathematics")
        self.assertIn("Concentration: Applied Mathematics", markdown)
        self.assertIn("Select one synthetic sequence.", markdown)
        self.assertIn("Select one additional modeling course.", markdown)


class DegreeAuditMarkdownTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = DegreeAuditSnapshot.model_validate(
            synthetic_snapshot_payload()
        )
        cls.markdown = render_degree_audit_markdown(cls.snapshot)

    def test_renders_all_llm_sections_and_nested_requirement_content(self) -> None:
        for expected in (
            "## Program",
            "## Progress Summary",
            "## Courses",
            "## Requirements",
            "## Warnings and Data Quality",
            "Statistics",
            "### 1. [IP] Program requirements",
            "#### 1.1. [OK] Synthetic core",
            "#### 1.2. [NO] Synthetic sequence choice",
            "Select one synthetic sequence.",
            "SYN 201, SYN 202",
            ">D (duplicated course)",
            ">Z",
            "UNKNOWN_FLAG",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.markdown)

        self.assertLess(
            self.markdown.index("Synthetic core"),
            self.markdown.index("Synthetic sequence choice"),
        )

    def test_markdown_omits_private_storage_and_source_details(self) -> None:
        for private_value in (
            "snapshot-synthetic",
            "a" * 64,
            "req-program",
            "attempt-completed",
            "synthetic-fixture",
            "10, 20, 100, 30",
        ):
            with self.subTest(private_value=private_value):
                self.assertNotIn(private_value, self.markdown)

    def test_json_renderer_matches_model_renderer(self) -> None:
        rendered_from_json = render_snapshot_json(snapshot_to_json(self.snapshot))

        self.assertEqual(rendered_from_json, self.markdown)
        self.assertEqual(
            render_degree_audit_markdown(self.snapshot),
            render_degree_audit_markdown(self.snapshot),
        )


if __name__ == "__main__":
    unittest.main()

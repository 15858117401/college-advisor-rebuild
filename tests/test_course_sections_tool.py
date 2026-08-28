import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.course_sections_tool import (
    CoursePageParseError,
    _fetch_html,
    _parse_course_page,
    get_course_sections,
)


class GetCourseSectionsInputTest(unittest.TestCase):
    def test_rejects_empty_course_list(self) -> None:
        with self.assertRaises(ValidationError):
            get_course_sections.invoke({"course_codes": []})

    def test_rejects_more_than_three_courses(self) -> None:
        with self.assertRaises(ValidationError):
            get_course_sections.invoke(
                {"course_codes": ["STAT 107", "STAT 200", "STAT 400", "STAT 410"]}
            )

    def test_rejects_invalid_course_code(self) -> None:
        with self.assertRaisesRegex(ValidationError, "expected a value like 'STAT 107'"):
            get_course_sections.invoke({"course_codes": ["not-a-course"]})

    def test_normalizes_course_code_without_a_space(self) -> None:
        validated = get_course_sections.args_schema.model_validate(
            {"course_codes": ["stat107"]}
        )
        self.assertEqual(validated.course_codes, ["STAT 107"])

    def test_tool_schema_advertises_one_to_three_courses(self) -> None:
        course_codes = get_course_sections.args_schema.model_json_schema()["properties"][
            "course_codes"
        ]

        self.assertEqual(course_codes["minItems"], 1)
        self.assertEqual(course_codes["maxItems"], 3)


class GetCourseSectionsLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.one_course = get_course_sections.invoke({"course_codes": [" stat 107 "]})
        cls.three_courses = get_course_sections.invoke(
            {"course_codes": ["STAT 107", "stat 200", "Stat 400"]}
        )
        cls.courses_without_sections = get_course_sections.invoke(
            {"course_codes": ["STAT 424", "STAT 999"]}
        )

    def test_queries_one_course(self) -> None:
        self.assertEqual(self.one_course[0]["course_code"], "STAT 107")
        self.assertGreater(len(self.one_course[0]["sections"]), 0)
        self.assertNotIn("error", self.one_course[0])

    def test_queries_three_courses_in_input_order(self) -> None:
        self.assertEqual(
            [item["course_code"] for item in self.three_courses],
            ["STAT 107", "STAT 200", "STAT 400"],
        )
        self.assertTrue(all("error" not in item for item in self.three_courses))

    def test_parses_section_fields(self) -> None:
        section = self.one_course[0]["sections"][0]

        self.assertEqual(section["section_type"], "Lecture")
        self.assertEqual(section["section"], "L1")
        self.assertEqual(section["crn"], "70317")
        self.assertEqual(section["days"], "MWF")
        self.assertEqual(section["time_start"], "10:00")
        self.assertEqual(section["time_end"], "10:50")
        self.assertEqual(section["location"], "THEAT Lincoln Hall")
        self.assertIn("Fagen-Ulmschneider, W", section["instructor"])

    def test_existing_course_without_sections_has_empty_list(self) -> None:
        result = self.courses_without_sections[0]

        self.assertEqual(result, {"course_code": "STAT 424", "sections": []})

    def test_nonexistent_course_returns_message(self) -> None:
        result = self.courses_without_sections[1]

        self.assertEqual(
            result,
            {
                "course_code": "STAT 999",
                "sections": [],
                "message": "no such course",
            },
        )


class GetCourseSectionsLiveFailureTest(unittest.TestCase):
    def test_upstream_http_failure_is_clear(self) -> None:
        missing_course_api = (
            "https://courses.illinois.edu/cisapp/explorer/schedule/"
            "2026/spring/STAT/999.xml"
        )

        with self.assertRaisesRegex(RuntimeError, "upstream returned HTTP 404"):
            _fetch_html(missing_course_api)

    def test_unexpected_live_page_is_rejected(self) -> None:
        home_page = _fetch_html("https://courses.illinois.edu/")

        with self.assertRaisesRegex(CoursePageParseError, "section table"):
            _parse_course_page(home_page)


class GetCourseSectionsErrorResultTest(unittest.TestCase):
    def test_maps_request_failure_to_error_result(self) -> None:
        with patch(
            "tools.course_sections_tool._fetch_html",
            side_effect=RuntimeError("network unavailable"),
        ):
            result = get_course_sections.invoke({"course_codes": ["STAT 107"]})

        self.assertEqual(
            result,
            [
                {
                    "course_code": "STAT 107",
                    "sections": [],
                    "error": {
                        "type": "request_failed",
                        "message": "network unavailable",
                    },
                }
            ],
        )

    def test_maps_parse_failure_to_error_result(self) -> None:
        with (
            patch("tools.course_sections_tool._fetch_html", return_value="<html>"),
            patch(
                "tools.course_sections_tool._parse_course_page",
                side_effect=CoursePageParseError("bad course page"),
            ),
        ):
            result = get_course_sections.invoke({"course_codes": ["STAT 107"]})

        self.assertEqual(
            result,
            [
                {
                    "course_code": "STAT 107",
                    "sections": [],
                    "error": {
                        "type": "response_parse_failed",
                        "message": "bad course page",
                    },
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()

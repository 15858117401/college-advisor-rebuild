import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nodes.advising import ADVISING_SKILLS, ADVISING_TOOLS
from nodes.catalog_lookup import CATALOG_SKILLS, CATALOG_TOOLS
from nodes.compose_response import COMPOSE_SYSTEM_PROMPT
from nodes.router import ROUTER_SYSTEM_PROMPT
from tools.professor_research_tools import (
    search_rate_my_professor,
    search_reddit,
)


class ProfessorResearchToolsTest(unittest.TestCase):
    @patch("tools.professor_research_tools.search_tavily")
    def test_rate_my_professor_keeps_only_matching_uiuc_professor(
        self, search_tavily
    ) -> None:
        search_tavily.return_value = {
            "results": [
                {
                    "title": "Albert Yu at University Of Illinois",
                    "url": "https://www.ratemyprofessors.com/professor/2596586",
                    "content": (
                        "Albert Yu, Statistics, University Of Illinois at "
                        "Urbana - Champaign, 84 ratings"
                    ),
                    "score": 0.9,
                },
                {
                    "title": "Albert Yu at Mission College",
                    "url": "https://www.ratemyprofessors.com/professor/1452336",
                    "content": "Albert Yu, Hospitality, Mission College",
                    "score": 0.8,
                },
                {
                    "title": "Search UIUC professors",
                    "url": "https://www.ratemyprofessors.com/search/professors/1112",
                    "content": "University of Illinois Urbana-Champaign",
                },
            ]
        }

        result = search_rate_my_professor.invoke(
            {"professor_name": "  Albert   Yu ", "course_code": "stat400"}
        )

        self.assertEqual(result["source"], "rate_my_professors")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(
            result["results"][0]["url"],
            "https://www.ratemyprofessors.com/professor/2596586",
        )
        query = search_tavily.call_args.args[0]
        self.assertIn('"Albert Yu"', query)
        self.assertIn('"STAT 400"', query)
        self.assertEqual(
            search_tavily.call_args.kwargs,
            {"include_domains": ["ratemyprofessors.com"]},
        )

    @patch("tools.professor_research_tools.search_tavily")
    def test_reddit_keeps_only_matching_r_uiuc_results(
        self, search_tavily
    ) -> None:
        search_tavily.return_value = {
            "results": [
                {
                    "title": "Stat 400 with Albert Yu",
                    "url": "https://www.reddit.com/r/UIUC/comments/example",
                    "content": "Albert Yu was discussed by UIUC students.",
                },
                {
                    "title": "Albert Yu elsewhere",
                    "url": "https://www.reddit.com/r/college/comments/example",
                    "content": "Albert Yu",
                },
                {
                    "title": "Different professor",
                    "url": "https://www.reddit.com/r/UIUC/comments/other",
                    "content": "David Unger",
                },
            ]
        }

        result = search_reddit.invoke({"professor_name": "Albert Yu"})

        self.assertEqual(result["source"], "reddit")
        self.assertEqual(len(result["results"]), 1)
        self.assertIn("site:reddit.com/r/UIUC", result["query"])
        self.assertEqual(
            search_tavily.call_args.kwargs,
            {"include_domains": ["reddit.com"]},
        )

    @patch("tools.professor_research_tools.search_tavily")
    def test_no_uiuc_match_does_not_substitute_other_school(
        self, search_tavily
    ) -> None:
        search_tavily.return_value = {
            "results": [
                {
                    "title": "David Douglas at Robert Morris University",
                    "url": "https://www.ratemyprofessors.com/professor/1989500",
                    "content": "David Douglas, Robert Morris University",
                },
                {
                    "title": "David Douglas at Concordia University",
                    "url": "https://www.ratemyprofessors.com/professor/492556",
                    "content": "David Douglas, Concordia University",
                },
            ]
        }

        result = search_rate_my_professor.invoke(
            {"professor_name": "David Douglas"}
        )

        self.assertEqual(result["results"], [])

    @patch("tools.professor_research_tools.search_tavily")
    def test_preserves_structured_search_error(self, search_tavily) -> None:
        search_tavily.return_value = {
            "results": [],
            "error": {
                "type": "configuration_error",
                "message": "TAVILY_API_KEY is required for professor research.",
            },
        }

        result = search_reddit.invoke({"professor_name": "Albert Yu"})

        self.assertEqual(result["results"], [])
        self.assertEqual(result["error"]["type"], "configuration_error")

    def test_validates_professor_and_course_inputs(self) -> None:
        with self.assertRaises(ValidationError):
            search_reddit.invoke({"professor_name": "  A  "})
        with self.assertRaises(ValidationError):
            search_rate_my_professor.invoke(
                {"professor_name": "Albert Yu", "course_code": "400"}
            )


class ProfessorResearchIntegrationTest(unittest.TestCase):
    def test_tools_are_registered_for_catalog_and_advising(self) -> None:
        expected = {"search_rate_my_professor", "search_reddit"}
        catalog_tool_names = {tool.name for tool in CATALOG_TOOLS}
        advising_tool_names = {tool.name for tool in ADVISING_TOOLS}

        self.assertTrue(expected.issubset(catalog_tool_names))
        self.assertEqual(advising_tool_names, catalog_tool_names)

    def test_skill_is_registered_for_catalog_and_advising(self) -> None:
        self.assertEqual(len(CATALOG_SKILLS), 1)
        self.assertEqual(CATALOG_SKILLS, ADVISING_SKILLS)
        self.assertIn("Never substitute a same-name professor", CATALOG_SKILLS[0])

    def test_compose_prompt_preserves_research_evidence(self) -> None:
        self.assertIn("Preserve source URLs", COMPOSE_SYSTEM_PROMPT)
        self.assertIn("sample-size caveats", COMPOSE_SYSTEM_PROMPT)

    def test_router_defines_direct_and_personalized_professor_routes(self) -> None:
        self.assertIn("public rating or student reviews", ROUTER_SYSTEM_PROMPT)
        self.assertIn("choosing or comparing instructors", ROUTER_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()

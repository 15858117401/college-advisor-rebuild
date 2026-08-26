import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph import graph


class RouterTest(unittest.TestCase):
    def test_graph_contains_expected_nodes(self) -> None:
        self.assertEqual(
            set(graph.get_graph().nodes),
            {
                "__start__",
                "router",
                "clarify",
                "catalog_lookup",
                "planning",
                "execute_tasks",
                "compose_response",
                "out_of_scope",
                "__end__",
            },
        )

    def assert_routes_to_clarify(self, user_input: str) -> None:
        result = graph.invoke({"user_input": user_input})
        self.assertEqual(result["route"], "clarify")

    def test_course_lookup_routes_to_clarify(self) -> None:
        self.assert_routes_to_clarify("What is STAT 400?")

    def test_weather_question_routes_to_clarify(self) -> None:
        self.assert_routes_to_clarify("今天天气怎么样？")

    def test_course_planning_routes_to_clarify(self) -> None:
        self.assert_routes_to_clarify("下一学期应该怎么选课？")


if __name__ == "__main__":
    unittest.main()

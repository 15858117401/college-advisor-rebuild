import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from react_agent import build_react_agent


class BuildReactAgentTest(unittest.TestCase):
    @patch("react_agent.create_agent")
    def test_registers_tools_and_appends_skills_to_prompt(
        self,
        create_agent,
    ) -> None:
        tools = [object(), object()]

        build_react_agent(
            "Base instructions.",
            tools=tools,
            skills=["First skill.", "  Second skill.  "],
        )

        call = create_agent.call_args.kwargs
        self.assertEqual(call["tools"], tools)
        self.assertEqual(
            call["system_prompt"],
            "Base instructions.\n\n# Skills\n\n"
            "First skill.\n\n---\n\nSecond skill.",
        )

    @patch("react_agent.create_agent")
    def test_skills_and_tools_are_optional(self, create_agent) -> None:
        build_react_agent("Base instructions.")

        call = create_agent.call_args.kwargs
        self.assertEqual(call["tools"], [])
        self.assertEqual(call["system_prompt"], "Base instructions.")


if __name__ == "__main__":
    unittest.main()

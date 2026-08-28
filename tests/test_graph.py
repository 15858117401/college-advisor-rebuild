import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage


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

    @patch("nodes.compose_response.llm_client")
    @patch("nodes.catalog_lookup.catalog_agent.invoke")
    def test_catalog_lookup_conversation(
        self,
        invoke_agent,
        invoke_compose,
    ) -> None:
        invoke_agent.return_value = {
            "messages": [AIMessage(content="STAT 400 is Statistics and Probability I.")]
        }
        invoke_compose.invoke.return_value = AIMessage(
            content="STAT 400 is Statistics and Probability I."
        )
        messages = [
            {"role": "user", "content": "We were discussing STAT courses."},
            {"role": "assistant", "content": "Which course interests you?"},
            {"role": "user", "content": "What is STAT 400?"},
        ]

        result = graph.invoke({"messages": messages})

        self.assertEqual(result["route"], "catalog_lookup")
        self.assertEqual(
            result["response"],
            "STAT 400 is Statistics and Probability I.",
        )
        agent_messages = invoke_agent.call_args.args[0]["messages"]
        self.assertEqual(
            [message.content for message in agent_messages],
            [message["content"] for message in messages],
        )


if __name__ == "__main__":
    unittest.main()

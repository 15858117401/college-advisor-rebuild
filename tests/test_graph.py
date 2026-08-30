import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph import graph
from nodes.out_of_scope import OUT_OF_SCOPE_RESPONSE, out_of_scope


class RouterTest(unittest.TestCase):
    def test_graph_contains_expected_nodes(self) -> None:
        self.assertEqual(
            set(graph.get_graph().nodes),
            {
                "__start__",
                "router",
                "clarify",
                "catalog_lookup",
                "advising",
                "compose_response",
                "out_of_scope",
                "__end__",
            },
        )

    def test_out_of_scope_returns_fixed_draft(self) -> None:
        self.assertEqual(
            out_of_scope({"current_input": "Write my essay.", "messages": []}),
            {"response": OUT_OF_SCOPE_RESPONSE},
        )

    @patch("nodes.compose_response.llm_client")
    @patch("nodes.router.llm_client")
    def test_out_of_scope_path_reaches_compose_response(
        self,
        router_llm,
        compose_llm,
    ) -> None:
        router_llm.invoke.return_value = AIMessage(
            content='{"route": "out_of_scope"}'
        )
        compose_llm.invoke.return_value = AIMessage(
            content=OUT_OF_SCOPE_RESPONSE
        )

        result = graph.invoke(
            {"current_input": "Write my essay.", "messages": []}
        )

        self.assertEqual(result["route"], "out_of_scope")
        self.assertEqual(result["response"], OUT_OF_SCOPE_RESPONSE)
        compose_prompt = compose_llm.invoke.call_args.args[0]
        self.assertEqual(compose_prompt[-1][1], OUT_OF_SCOPE_RESPONSE)

    @patch("nodes.compose_response.llm_client")
    @patch("nodes.advising.advising_agent.invoke")
    @patch("nodes.router.llm_client")
    def test_advising_path_reaches_compose_response(
        self,
        router_llm,
        invoke_agent,
        compose_llm,
    ) -> None:
        router_llm.invoke.return_value = AIMessage(
            content='{"route": "advising"}'
        )
        invoke_agent.return_value = {
            "messages": [AIMessage(content="Take STAT 410 next.")]
        }
        compose_llm.invoke.return_value = AIMessage(
            content="Take STAT 410 next."
        )

        past_messages = [
            {"role": "user", "content": "I have completed STAT 400."},
            {"role": "assistant", "content": "What is your goal?"},
        ]
        current_input = "What should I take next?"
        result = graph.invoke(
            {
                "current_input": current_input,
                "messages": past_messages,
            }
        )

        self.assertEqual(result["route"], "advising")
        self.assertEqual(result["response"], "Take STAT 410 next.")
        agent_messages = invoke_agent.call_args.args[0]["messages"]
        self.assertEqual(
            [message.content for message in agent_messages],
            [
                *[message["content"] for message in past_messages],
                current_input,
            ],
        )
        router_messages = router_llm.invoke.call_args.args[0]
        self.assertEqual(router_messages[-1].content, current_input)
        compose_prompt = compose_llm.invoke.call_args.args[0]
        self.assertEqual(compose_prompt[-1][1], "Take STAT 410 next.")

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
        past_messages = [
            {"role": "user", "content": "We were discussing STAT courses."},
            {"role": "assistant", "content": "Which course interests you?"},
        ]
        current_input = "What is STAT 400?"

        result = graph.invoke(
            {
                "current_input": current_input,
                "messages": past_messages,
            }
        )

        self.assertEqual(result["route"], "catalog_lookup")
        self.assertEqual(
            result["response"],
            "STAT 400 is Statistics and Probability I.",
        )
        agent_messages = invoke_agent.call_args.args[0]["messages"]
        self.assertEqual(
            [message.content for message in agent_messages],
            [
                *[message["content"] for message in past_messages],
                current_input,
            ],
        )


if __name__ == "__main__":
    unittest.main()

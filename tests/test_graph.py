import json
from copy import deepcopy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph import graph
from nodes.out_of_scope import OUT_OF_SCOPE_RESPONSE, out_of_scope
from nodes.planner import PLANNER_SYSTEM_PROMPT, planner
from state import profile_from_runtime, profile_reference_message


class RouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = {
            "major": "Mathematics", "completed_courses": ["STAT 400"],
            "cumulative_gpa": 3.0, "major_gpa": 3.0,
        }
        profile_patch = patch("state.load_local_profile", return_value=self.profile)
        profile_patch.start()
        self.addCleanup(profile_patch.stop)

    def test_graph_contains_expected_nodes(self) -> None:
        self.assertEqual(
            set(graph.get_graph().nodes),
            {
                "__start__",
                "router",
                "planner",
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

    @patch("nodes.planner.llm_client")
    def test_planner_rewrites_only_current_request_with_separate_history(self, planner_llm) -> None:
        state = {
            "current_input": "Actually, make it one of those plus a U.S. minority course.",
            "messages": [
                {"role": "user", "content": "Recommend two statistics courses."},
                AIMessage(content="Do you have any other requirements?"),
            ],
            "route": "advising",
            "request_brief": "An outdated rewrite from a previous turn.",
        }
        original = deepcopy(state)
        brief = "Recommend 2 courses: 1 statistics course and 1 U.S. minority course."
        planner_llm.invoke.return_value = AIMessage(content=f"\n{brief}\n")

        self.assertEqual(planner(state), {"request_brief": brief})
        self.assertEqual(state, original)
        planner_llm.invoke.assert_called_once()
        sent = planner_llm.invoke.call_args.args[0]
        self.assertEqual(sent[0], ("system", PLANNER_SYSTEM_PROMPT))
        self.assertEqual(
            json.loads(sent[1].content),
            {
                "conversation_context": [
                    {"role": "user", "content": "Recommend two statistics courses."},
                    {"role": "assistant", "content": "Do you have any other requirements?"},
                ],
                "current_input": state["current_input"],
            },
        )

    @patch("nodes.compose_response.llm_client")
    @patch("nodes.planner.llm_client")
    @patch("nodes.router.llm_client")
    def test_out_of_scope_path_reaches_compose_response(
        self,
        router_llm,
        planner_llm,
        compose_llm,
    ) -> None:
        router_llm.invoke.return_value = AIMessage(
            content='{"route": "out_of_scope"}'
        )
        planner_llm.invoke.return_value = AIMessage(content="Write an essay.")
        compose_llm.invoke.return_value = AIMessage(
            content=OUT_OF_SCOPE_RESPONSE
        )

        result = graph.invoke(
            {"current_input": "Write my essay.", "messages": []}
        )

        self.assertEqual(result["route"], "out_of_scope")
        self.assertEqual(result["response"], OUT_OF_SCOPE_RESPONSE)
        compose_prompt = compose_llm.invoke.call_args.args[0]
        self.assertEqual(json.loads(compose_prompt[-1][1])["draft"], OUT_OF_SCOPE_RESPONSE)
        planner_llm.invoke.assert_called_once()

    @patch("nodes.compose_response.llm_client")
    @patch("nodes.advising.advising_agent.invoke")
    @patch("nodes.planner.llm_client")
    @patch("nodes.router.llm_client")
    def test_advising_path_reaches_compose_response(
        self,
        router_llm,
        planner_llm,
        invoke_agent,
        compose_llm,
    ) -> None:
        router_llm.invoke.return_value = AIMessage(
            content='{"route": "advising"}'
        )
        brief = "Recommend the next course after completing STAT 400."
        planner_llm.invoke.return_value = AIMessage(content=brief)
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
                "request_brief": "Old request brief that must be replaced.",
            }
        )

        self.assertEqual(result["route"], "advising")
        self.assertEqual(result["response"], "Take STAT 410 next.")
        self.assertEqual(result["request_brief"], brief)
        self.assertEqual(result["current_input"], current_input)
        self.assertEqual(
            [m.content for m in result["messages"]],
            [m["content"] for m in past_messages],
        )
        profile = self.profile
        agent_messages = invoke_agent.call_args.args[0]["messages"]
        self.assertEqual(
            [message.content for message in agent_messages[:-2]],
            [
                profile_reference_message(profile).content,
                *[message["content"] for message in past_messages],
            ],
        )
        self.assertIsInstance(agent_messages[-2], AIMessage)
        self.assertEqual(agent_messages[-2].name, "planner")
        self.assertIn(brief, agent_messages[-2].content)
        self.assertEqual(agent_messages[-1].content, current_input)
        router_messages = router_llm.invoke.call_args.args[0]
        router_input = json.loads(router_messages[-1].content)
        self.assertEqual(
            router_input,
            {
                "conversation_context": past_messages,
                "current_input": current_input,
                "profile": profile,
            },
        )
        compose_prompt = compose_llm.invoke.call_args.args[0]
        compose_input = json.loads(compose_prompt[-1][1])
        self.assertEqual(compose_input["draft"], "Take STAT 410 next.")
        self.assertEqual(compose_input["current_input"], current_input)
        self.assertEqual(
            [m["content"] for m in compose_input["conversation_context"]],
            [m["content"] for m in past_messages],
        )
        planner_llm.invoke.assert_called_once()

    @patch("nodes.compose_response.llm_client")
    @patch("nodes.catalog_lookup.catalog_agent.invoke")
    @patch("nodes.planner.llm_client")
    @patch("nodes.router.llm_client")
    def test_catalog_lookup_conversation(
        self,
        router_llm,
        planner_llm,
        invoke_agent,
        invoke_compose,
    ) -> None:
        router_llm.invoke.return_value = AIMessage(
            content='{"route": "catalog_lookup"}'
        )
        brief = "Describe STAT 400."
        planner_llm.invoke.return_value = AIMessage(content=brief)
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
        profile = self.profile
        agent_messages = invoke_agent.call_args.args[0]["messages"]
        self.assertEqual(
            [message.content for message in agent_messages[:-2]],
            [
                profile_reference_message(profile).content,
                *[message["content"] for message in past_messages],
            ],
        )
        self.assertIsInstance(agent_messages[-2], AIMessage)
        self.assertIn(brief, agent_messages[-2].content)
        self.assertEqual(agent_messages[-1].content, current_input)
        planner_llm.invoke.assert_called_once()






def test_explicit_profile_none_disables_fallback_but_omission_preserves_it():
    profile = {'major': 'Statistics', 'completed_courses': ['STAT 400'], 'cumulative_gpa': 2.71, 'major_gpa': 2.8}
    with patch('state.load_local_profile', return_value=profile) as load:
        assert profile_from_runtime(Runtime(context={'profile': None})) is None
        load.assert_not_called()
        assert profile_from_runtime(Runtime(context={})) == profile
        assert profile_from_runtime() == profile
        assert load.call_count == 2


def test_profile_suppression_reaches_router_and_advising():
    with (
        patch('state.load_local_profile', side_effect=AssertionError('must not load local profile')),
        patch('nodes.router.llm_client') as router_llm,
        patch('nodes.planner.llm_client') as planner_llm,
        patch('nodes.advising.advising_agent.invoke') as advise,
        patch('nodes.compose_response.llm_client') as compose,
    ):
        router_llm.invoke.return_value = AIMessage(content='{"route":"advising"}')
        planner_llm.invoke.return_value = AIMessage(content='Plan next semester for a hypothetical Economics student.')
        advise.return_value = {'messages': [AIMessage(content='Economics plan')]}
        compose.invoke.return_value = AIMessage(content='Economics plan')
        query = 'For a hypothetical Economics student, plan next semester.'
        graph.invoke({'current_input': query, 'messages': []}, context={'profile': None})
    assert json.loads(router_llm.invoke.call_args.args[0][-1].content)['profile'] is None
    sent = advise.call_args.args[0]['messages']
    assert [m.type for m in sent] == ['ai', 'human']
    assert sent[0].name == 'planner'
    assert sent[-1].content == query


def test_conflicting_scenario_is_preserved_and_profile_stays_read_only():
    from nodes.advising import ADVISING_SYSTEM_PROMPT
    from nodes.router import ROUTER_SYSTEM_PROMPT

    profile = {'major': 'Statistics', 'completed_courses': ['STAT 400'], 'cumulative_gpa': 2.71, 'major_gpa': 2.8}
    original = deepcopy(profile)
    query = 'For another student majoring in Economics, recommend courses. Their GPA is unknown.'
    with (
        patch('nodes.router.llm_client') as router_llm,
        patch('nodes.planner.llm_client') as planner_llm,
        patch('nodes.advising.advising_agent.invoke') as advise,
        patch('nodes.compose_response.llm_client') as compose,
    ):
        router_llm.invoke.return_value = AIMessage(content='{"route":"advising"}')
        planner_llm.invoke.return_value = AIMessage(content=query)
        advise.return_value = {'messages': [AIMessage(content='Economics plan')]}
        compose.invoke.return_value = AIMessage(content='Economics plan')
        graph.invoke({'current_input': query, 'messages': []}, context={'profile': profile})
    assert profile == original
    assert json.loads(router_llm.invoke.call_args.args[0][-1].content)['current_input'] == query
    sent = advise.call_args.args[0]['messages']
    assert sent[-1].content == query
    assert 'takes precedence' in sent[0].content
    assert 'do not fill' in sent[0].content
    assert 'precedence' in ADVISING_SYSTEM_PROMPT
    assert 'precedence' in ROUTER_SYSTEM_PROMPT


def test_compose_separates_request_history_and_draft_and_only_updates_response():
    from nodes.compose_response import compose_response

    state = {
        "current_input": "And how many credits is it?",
        "messages": [
            {"role": "user", "content": "Tell me about MATH 416."},
            AIMessage(content="It is Abstract Linear Algebra."),
        ],
        "response": "Three or four credits with approval for four. Extra course descriptions and offers.",
        "route": "catalog_lookup",
    }
    with patch("nodes.compose_response.llm_client") as llm:
        llm.invoke.return_value = AIMessage(content="3 credits, or 4 with approval.")
        result = compose_response(state)
    payload = json.loads(llm.invoke.call_args.args[0][-1][1])
    assert payload["current_input"] == state["current_input"]
    assert payload["draft"] == state["response"]
    assert [m["role"] for m in payload["conversation_context"]] == ["human", "ai"]
    assert len(payload["conversation_context"]) == 2
    assert result == {"response": "3 credits, or 4 with approval."}
    assert state["route"] == "catalog_lookup"


if __name__ == "__main__":
    unittest.main()

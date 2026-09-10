import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from react_agent import build_react_agent
import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool, ToolException
from tools.course_details_tool import GetCourseDetailsInput


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




# Exercise the real agent/tool loop without network calls.


class ScriptedToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.mark.parametrize('invalid_code', ['MATH-416', 'MATH 999'])
def test_agent_recovers_from_validation_and_unsupported_resource(invalid_code):
    calls = []

    @tool(args_schema=GetCourseDetailsInput)
    def lookup(course_codes: list[str]) -> str:
        """Look up a course."""
        calls.append(course_codes)
        if course_codes == ['MATH 999']:
            raise ToolException('No stored resource. Try a supported course.')
        return 'Abstract Linear Algebra'

    model = ScriptedToolModel(responses=[
        AIMessage(content='', tool_calls=[{'name': 'lookup', 'args': {'course_codes': [invalid_code]}, 'id': 'bad'}]),
        AIMessage(content='', tool_calls=[{'name': 'lookup', 'args': {'course_codes': ['MATH416']}, 'id': 'good'}]),
        AIMessage(content='Abstract Linear Algebra'),
    ])
    with patch('react_agent.llm_client', model):
        agent = build_react_agent('Repair invalid requests.', tools=[lookup])
    result = agent.invoke({'messages': [('human', 'Find MATH 416.')]})
    messages = [message for message in result['messages'] if isinstance(message, ToolMessage)]
    assert messages[0].status == 'error'
    assert messages[0].tool_call_id == 'bad'
    assert messages[1].status == 'success'
    assert calls[-1] == ['MATH 416']
    assert result['messages'][-1].content == 'Abstract Linear Algebra'


@pytest.mark.parametrize('error', [RuntimeError('service unavailable'), ValueError('programming failure')])
def test_unexpected_tool_failures_propagate(error):
    @tool
    def broken() -> str:
        """Exercise an unexpected failure."""
        raise error

    model = ScriptedToolModel(responses=[AIMessage(content='', tool_calls=[{'name': 'broken', 'args': {}, 'id': 'broken'}])])
    with patch('react_agent.llm_client', model):
        agent = build_react_agent('Call the tool.', tools=[broken])
    with pytest.raises(type(error), match=str(error)):
        agent.invoke({'messages': [('human', 'Call the tool.')]})


if __name__ == "__main__":
    unittest.main()

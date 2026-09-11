from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import ToolException, tool
from pydantic import Field

from nodes.advising import ADVISING_SYSTEM_PROMPT, ADVISING_TOOLS
from nodes.catalog_lookup import CATALOG_SYSTEM_PROMPT, CATALOG_TOOLS
from react_agent import build_react_agent
from tools.skill_loader_tool import SKILL_DESCRIPTIONS, load_skill


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFESSOR_SKILL_PATH = (
    PROJECT_ROOT / "skills" / "professor-research" / "professor_research.md"
)
SKILL_BODY_MARKER = "Never substitute a same-name professor"


def test_load_skill_returns_packaged_file() -> None:
    assert load_skill.invoke({"skill_name": "professor-research"}) == (
        PROFESSOR_SKILL_PATH.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("skill_name", ["missing", "../professor-research"])
def test_load_skill_rejects_unknown_name(skill_name: str) -> None:
    with pytest.raises(ToolException, match="Unknown skill"):
        load_skill.invoke({"skill_name": skill_name})


def test_only_advising_receives_skill_metadata_and_loader() -> None:
    description = SKILL_DESCRIPTIONS["professor-research"]
    assert description in ADVISING_SYSTEM_PROMPT
    assert SKILL_BODY_MARKER not in ADVISING_SYSTEM_PROMPT
    assert "load_skill" in {tool.name for tool in ADVISING_TOOLS}

    assert description not in CATALOG_SYSTEM_PROMPT
    assert "load_skill" not in {tool.name for tool in CATALOG_TOOLS}


class RecordingToolModel(FakeMessagesListChatModel):
    seen_calls: list[list] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, **kwargs):
        self.seen_calls.append(list(messages))
        return super()._generate(messages, **kwargs)


@tool
def continue_work(step: int) -> str:
    """Continue an ordinary advising step before loading a skill."""
    return f"completed step {step}"


def message_text(messages: list) -> str:
    return "\n".join(str(message.content) for message in messages)


@pytest.mark.parametrize("load_iteration", [2, 5, 10])
def test_skill_can_load_on_any_react_iteration(load_iteration: int) -> None:
    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "continue_work",
                    "args": {"step": iteration},
                    "id": f"continue-{iteration}",
                }
            ],
        )
        for iteration in range(1, load_iteration)
    ]
    responses.extend(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "load_skill",
                        "args": {"skill_name": "professor-research"},
                        "id": "load-skill",
                    }
                ],
            ),
            AIMessage(content="finished with skill"),
        ]
    )
    model = RecordingToolModel(responses=responses)
    with patch("react_agent.llm_client", model):
        agent = build_react_agent(
            ADVISING_SYSTEM_PROMPT,
            tools=[continue_work, load_skill],
        )

    result = agent.invoke(
        {"messages": [("human", "Compare instructors.")]},
        config={"recursion_limit": 24},
    )

    assert result["messages"][-1].content == "finished with skill"
    for call in model.seen_calls[:load_iteration]:
        assert SKILL_BODY_MARKER not in message_text(call)
    assert any(
        isinstance(message, ToolMessage)
        and SKILL_BODY_MARKER in str(message.content)
        for message in model.seen_calls[-1]
    )
    assert all(
        SKILL_BODY_MARKER not in str(message.content)
        for call in model.seen_calls
        for message in call
        if isinstance(message, SystemMessage)
    )

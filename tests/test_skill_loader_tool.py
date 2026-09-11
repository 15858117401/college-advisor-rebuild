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
from tools.skill_loader_tool import SKILL_DESCRIPTIONS, _discover_skills, load_skill


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_CASES = [
    (
        "professor-research",
        PROJECT_ROOT / "skills" / "professor_research.md",
        "Never substitute a same-name professor",
    ),
    (
        "scheduling",
        PROJECT_ROOT / "skills" / "one_semester_schedule.md",
        "Resolve conflicts by trying other sections",
    ),
    (
        "course_and_section_recommendation",
        PROJECT_ROOT / "skills" / "course_and_section_recommendation.md",
        "Each group requires one separate",
    ),
    (
        "planner",
        PROJECT_ROOT / "skills" / "planner.md",
        "Place prerequisite courses in earlier semesters",
    ),
]


@pytest.mark.parametrize("skill_name,skill_path,body_marker", SKILL_CASES)
def test_load_skill_returns_packaged_file(skill_name, skill_path, body_marker) -> None:
    assert load_skill.invoke({"skill_name": skill_name}) == (
        skill_path.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "skill_name",
    [
        "missing",
        "../professor-research",
        "Scheduling",
        "one_semester_schedule.md",
        "Course_And_Section_Recommendation",
        "course_and_section_recommendation.md",
        "Planner",
        "planner.md",
    ],
)
def test_load_skill_rejects_unknown_name(skill_name: str) -> None:
    with pytest.raises(ToolException, match="Unknown skill"):
        load_skill.invoke({"skill_name": skill_name})


@pytest.mark.parametrize("skill_name,skill_path,body_marker", SKILL_CASES)
def test_only_advising_receives_skill_metadata_and_loader(
    skill_name, skill_path, body_marker,
) -> None:
    description = SKILL_DESCRIPTIONS[skill_name]
    assert f"`{skill_name}`: {description}" in ADVISING_SYSTEM_PROMPT
    assert description in ADVISING_SYSTEM_PROMPT
    assert body_marker not in ADVISING_SYSTEM_PROMPT
    assert "load_skill" in {tool.name for tool in ADVISING_TOOLS}

    assert description not in CATALOG_SYSTEM_PROMPT
    assert body_marker not in CATALOG_SYSTEM_PROMPT
    assert "load_skill" not in {tool.name for tool in CATALOG_TOOLS}


def test_discovery_uses_frontmatter_and_caches_full_files(tmp_path) -> None:
    content = (
        '---\nname: "custom-skill"\ndescription: >-\n'
        '  A reusable workflow\n  with a folded description.\n---\n\n'
        '# Instructions\nname: not-the-canonical-name\n'
    )
    skill_path = tmp_path / "unrelated_filename.md"
    skill_path.write_text(content, encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("Not a skill", encoding="utf-8")
    nested = tmp_path / "old_layout"
    nested.mkdir()
    (nested / "nested.md").write_text("Not a direct skill", encoding="utf-8")

    skills, descriptions = _discover_skills(tmp_path)

    assert skills == {"custom-skill": content}
    assert descriptions == {
        "custom-skill": "A reusable workflow with a folded description."
    }
    updated_content = content + "New instructions.\n"
    skill_path.write_text(updated_content, encoding="utf-8")
    with patch("tools.skill_loader_tool.SKILLS", skills):
        assert load_skill.invoke({"skill_name": "custom-skill"}) == content
    assert _discover_skills(tmp_path)[0]["custom-skill"] == updated_content


@pytest.mark.parametrize(
    "content",
    [
        "# No frontmatter\nname: test\ndescription: test\n",
        "---\nname: test\ndescription: test\n",
        "---\nname: [\ndescription: test\n---\n",
        "---\n- test\n---\n",
        "---\nname: test\n---\n",
        "---\nname: ' '\ndescription: test\n---\n",
        "---\nname: test\ndescription: ''\n---\n",
        "---\nname: test\ndescription: 123\n---\n",
    ],
)
def test_discovery_rejects_invalid_metadata_with_file_context(tmp_path, content) -> None:
    (tmp_path / "invalid.md").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="invalid.md"):
        _discover_skills(tmp_path)


def test_discovery_rejects_duplicate_canonical_names(tmp_path) -> None:
    for filename in ("first.md", "second.md"):
        (tmp_path / filename).write_text(
            "---\nname: same-name\ndescription: A workflow.\n---\nInstructions.\n",
            encoding="utf-8",
        )
    with pytest.raises(ValueError, match="Duplicate skill name 'same-name'"):
        _discover_skills(tmp_path)


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
@pytest.mark.parametrize("skill_name,skill_path,body_marker", SKILL_CASES)
def test_skill_can_load_on_any_react_iteration(
    load_iteration, skill_name, skill_path, body_marker,
) -> None:
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
                        "args": {"skill_name": skill_name},
                        "id": "load-skill",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "continue_work",
                        "args": {"step": load_iteration + 1},
                        "id": "after-loading",
                    }
                ],
            ),
            AIMessage(content="finished with skill"),
            AIMessage(content="new invocation without loading"),
        ]
    )
    model = RecordingToolModel(responses=responses)
    with patch("react_agent.llm_client", model):
        agent = build_react_agent(
            ADVISING_SYSTEM_PROMPT,
            tools=[continue_work, load_skill],
        )

    result = agent.invoke(
        {"messages": [("human", "Help with my semester.")]},
        config={"recursion_limit": 24},
    )

    assert result["messages"][-1].content == "finished with skill"
    for call in model.seen_calls[:load_iteration]:
        assert body_marker not in message_text(call)
    for call in model.seen_calls[load_iteration:]:
        assert any(
            isinstance(message, ToolMessage)
            and message.content == skill_path.read_text(encoding="utf-8")
            for message in call
        )
    assert all(
        body_marker not in str(message.content)
        for call in model.seen_calls
        for message in call
        if isinstance(message, SystemMessage)
    )

    next_result = agent.invoke({"messages": [("human", "A separate user turn.")]})
    assert next_result["messages"][-1].content == "new invocation without loading"
    assert body_marker not in message_text(model.seen_calls[-1])

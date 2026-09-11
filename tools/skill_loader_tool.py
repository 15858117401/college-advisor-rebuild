from pathlib import Path

from langchain_core.tools import ToolException, tool


SKILLS_DIRECTORY = Path(__file__).resolve().parents[1] / "skills"
SKILLS = {
    skill_file.parent.name: skill_file.read_text(encoding="utf-8")
    for skill_file in sorted(SKILLS_DIRECTORY.glob("*/professor_research.md"))
}
SKILL_DESCRIPTIONS = {
    name: next(
        line.split(":", 1)[1].strip()
        for line in content.splitlines()
        if line.startswith("description:")
    )
    for name, content in SKILLS.items()
}


@tool
def load_skill(skill_name: str) -> str:
    """Load one available advising skill by its exact name."""
    content = SKILLS.get(skill_name)
    if content is None:
        available = ", ".join(SKILLS) or "none"
        raise ToolException(
            f"Unknown skill {skill_name!r}. Available skills: {available}."
        )
    return content


__all__ = [
    "SKILL_DESCRIPTIONS",
    "SKILLS",
    "SKILLS_DIRECTORY",
    "load_skill",
]

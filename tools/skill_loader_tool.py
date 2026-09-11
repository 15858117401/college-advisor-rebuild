from pathlib import Path

from langchain_core.tools import ToolException, tool
from yaml import YAMLError, safe_load


SKILLS_DIRECTORY = Path(__file__).resolve().parents[1] / "skills"


def _discover_skills(directory: Path) -> tuple[dict[str, str], dict[str, str]]:
    skills: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    for skill_file in sorted(directory.glob("*.md")):
        content = skill_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        if not lines or lines[0] != "---":
            raise ValueError(f"Skill {skill_file} must start with YAML frontmatter.")
        try:
            end = lines.index("---", 1)
            metadata = safe_load("\n".join(lines[1:end]))
        except (ValueError, YAMLError) as exc:
            raise ValueError(f"Invalid YAML frontmatter in skill {skill_file}.") from exc
        if not isinstance(metadata, dict) or any(
            not isinstance(metadata.get(field), str) or not metadata[field].strip()
            for field in ("name", "description")
        ):
            raise ValueError(
                f"Skill {skill_file} requires nonempty name and description strings."
            )
        name = metadata["name"].strip()
        if name in skills:
            raise ValueError(f"Duplicate skill name {name!r} in {skill_file}.")
        skills[name] = content
        descriptions[name] = metadata["description"].strip()
    return skills, descriptions


SKILLS, SKILL_DESCRIPTIONS = _discover_skills(SKILLS_DIRECTORY)


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

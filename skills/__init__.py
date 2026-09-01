from pathlib import Path


SKILLS_DIRECTORY = Path(__file__).resolve().parent


def load_skill(skill_directory: str) -> str:
    """Load a runtime skill's SKILL.md text."""
    if not skill_directory or Path(skill_directory).name != skill_directory:
        raise ValueError("invalid skill directory")
    return (SKILLS_DIRECTORY / skill_directory / "SKILL.md").read_text(
        encoding="utf-8"
    )


__all__ = ["load_skill"]

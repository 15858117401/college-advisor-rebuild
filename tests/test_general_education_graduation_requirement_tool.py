from nodes.advising import ADVISING_TOOLS
from nodes.catalog_lookup import CATALOG_TOOLS
from tools.general_education_graduation_requirement_tool import (
    LAS_GENERAL_EDUCATION_GRADUATION_REQUIREMENT,
    general_education_graduation_requirement,
)


def test_general_education_graduation_requirement_has_no_parameters() -> None:
    assert general_education_graduation_requirement.args == {}


def test_general_education_graduation_requirement_returns_fixed_markdown() -> None:
    assert (
        general_education_graduation_requirement.invoke({})
        == LAS_GENERAL_EDUCATION_GRADUATION_REQUIREMENT
    )


def test_general_education_graduation_requirement_is_registered() -> None:
    tool_name = "general_education_graduation_requirement"
    assert tool_name in {catalog_tool.name for catalog_tool in CATALOG_TOOLS}
    assert tool_name in {advising_tool.name for advising_tool in ADVISING_TOOLS}

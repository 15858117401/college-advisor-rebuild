from langchain_core.tools import tool


LAS_GENERAL_EDUCATION_GRADUATION_REQUIREMENT = r"""### LAS gen ed requirements

LAS students generally have a great deal of flexibility in fulfilling their general education requirements, which include the following:

- [**Non-Primary Language**](https://las.illinois.edu/academics/requirements/language) \
  four levels of one language or three levels of two different languages
- [**Composition I**](https://las.illinois.edu/academics/requirements/comp)
- [**Advanced Composition&#xA0;**](https://las.illinois.edu/academics/requirements/advancedcomp)[(ACP)](https://las.illinois.edu/academics/requirements/advancedcomp) \
  Some curricula may require a specific course
- **6 hours Humanities & Arts&#xA0;**(HP or LA)\
  Historical & Philosophical Perspectives\
  Literature & the Arts
- **6 hours Social & Behavioral Sciences&#xA0;**(SS or BS)\
  Social Sciences \
  Behavioral Sciences
- **6 hours Natural Sciences & Technology&#xA0;**(LS or PS)\
  Life Sciences \
  Physical Sciences
- **Quantitative Reasoning I** (QR1)\
  One course
- **Quantitative Reasoning II** (QR1 or QR2)\
  One course

Students beginning at Illinois in **summer 2018 and beyond** must complete three cultural studies courses:

- **Western Cultures** (W)
- **Non-Western Cultures** (NW)
- **U.S. Minority Cultures** (US)

Students who entered Illinois **during or before the spring 2018 term** must complete:

- **Western Cultures&#xA0;**(W)\
  One course
- **Non-Western Cultures/U.S. Minority** (NW or US)\
  One course"""


@tool("general_education_graduation_requirement")
def general_education_graduation_requirement() -> str:
    """Return the fixed LAS general education graduation requirements.

    Use this tool whenever LAS general education requirements are needed.
    It takes no parameters.
    """
    return LAS_GENERAL_EDUCATION_GRADUATION_REQUIREMENT


__all__ = [
    "LAS_GENERAL_EDUCATION_GRADUATION_REQUIREMENT",
    "general_education_graduation_requirement",
]

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nodes.catalog_lookup import catalog_agent


CASES = [
    "What are the credits and prerequisites for STAT 400?",

    "Return only the course codes and credits for 400-level STAT courses ",
    
    "list course that worth 4 credits that STAT 400 as a prerequisite.",

    "List the Spring 2026 sections, CRNs, and meeting times for STAT 107.",

    "Give me the historical instructor average GPAs for STAT 420. ",

    "For STAT 420, give me both the Spring 2026 section meeting times and the historical instructor average GPAs. Do not treat GPA records as course sections."
]
CASE = 6


def test_agent():
    user_input = CASES[CASE - 1]
    result = catalog_agent.invoke(
        {"messages": [{"role": "user", "content": user_input}]}
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    test_agent()

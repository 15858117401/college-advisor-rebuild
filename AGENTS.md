# Project Instructions

- `college_advisor/` is the previous Java implementation. Use it only as a read-only reference; do not modify it.
- Write the new Python implementation in this repository root and its normal subdirectories, outside `college_advisor/`.
- Keep changes minimal. Do not add files, dependencies, configuration, or project structure unless the user explicitly asks for them.
- Place small local smoke or unit tests in `tests/`. These tests are for simple implementation verification, not evaluation or benchmark suites.
- Put Python tools in the lowercase `tools/` package, with their unit tests in `tests/` (for example, `tools/course_sections_tool.py` is tested by `tests/test_course_sections_tool.py`).
- Keep `graph.py` focused on graph assembly: node registration, edges, compilation, and exports. Do not place node business logic or LLM calls in it.
- Put each graph node implementation in its own module under the lowercase `nodes/` package.
- Centralize LLM initialization in `llm_client.py`. Nodes that need an LLM must import and reuse the shared `llm_client` instead of creating their own model client.


## Project Overview

This project rebuilds the college-advising agent in Python as a LangGraph workflow. A request enters the graph through the router, moves to a specialized node, and then either asks the user for more information or produces a response. `graph.py` defines this flow, `state.py` defines shared graph state, and `nodes/` contains the node implementations.

- **Router:** Classifies the user's request and selects the appropriate next node. It should only make a routing decision and should not answer the request or perform node business logic.
- **Catalog Lookup:** Handles direct, factual questions about the course catalog, such as course details, prerequisites, sections, instructors, and graduation requirements. It retrieves information without creating a personalized course or degree plan.

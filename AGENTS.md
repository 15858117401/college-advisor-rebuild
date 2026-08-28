# Project Instructions

- `college_advisor/` is the previous Java implementation. Use it only as a read-only reference; do not modify it.
- Write the new Python implementation in this repository root and its normal subdirectories, outside `college_advisor/`.
- Keep changes minimal. Do not add files, dependencies, configuration, or project structure unless the user explicitly asks for them.
- Place small local smoke or unit tests in `tests/`. These tests are for simple implementation verification, not evaluation or benchmark suites.
- Put only agent-callable runtime tools in the lowercase `tools/` package, with their unit tests in `tests/` (for example, `tools/course_sections_tool.py` is tested by `tests/test_course_sections_tool.py`).
- Put all current and future Supabase-related code in `Supabase/`, including SQL schemas, migrations, database clients/helpers, validation scripts, and import/upload scripts. Never place this code in `tools/`; `tools/` is reserved exclusively for tools the advising agent can call at runtime.
- Keep `graph.py` focused on graph assembly: node registration, edges, compilation, and exports. Do not place node business logic or LLM calls in it.
- Put each graph node implementation in its own module under the lowercase `nodes/` package.
- Centralize LLM initialization in `llm_client.py`. Nodes that need an LLM must import and reuse the shared `llm_client` instead of creating their own model client.
- `Resource/` stores course catalog, offering availability, and course/instructor GPA statistics used as reference data by the advising agent.


## Uploading Resources to Supabase

Local files under `Resource/` are the source of truth. Keep credentials in the uncommitted `.env` file and never print or commit their values.

The resource upload scripts expect `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. Statistics embedding checks and uploads also require `OPENAI_API_KEY`.

Before the first upload, or after a schema change, apply the corresponding SQL file to the target Supabase project. Then run the importer from the repository root with the project virtual environment:

```bash
# Course and instructor statistics
.venv/bin/python -m Supabase.import_stat_resources validate
.venv/bin/python -m Supabase.import_stat_resources smoke
.venv/bin/python -m Supabase.import_stat_resources upload

# Graduation-requirement Markdown documents
.venv/bin/python -m Supabase.import_graduation_requirements validate
.venv/bin/python -m Supabase.import_graduation_requirements upload
```

Apply `Supabase/stat_resource_schema.sql` for statistics resources and `Supabase/graduation_requirements_schema.sql` for graduation-requirement documents. The graduation importer reads `Resource/graduation_requirements/manifest.json`, uploads the shared LAS document before its two child program documents, and verifies that the Markdown read back from Supabase exactly matches the local files.


## Project Overview

This project rebuilds the college-advising agent in Python as a LangGraph workflow. A request enters the graph through the router, moves to a specialized node, and then either asks the user for more information or produces a response. `graph.py` defines this flow, `state.py` defines shared graph state, and `nodes/` contains the node implementations.

- **Router:** Classifies the user's request and selects the appropriate next node. It should only make a routing decision and should not answer the request or perform node business logic.
- **Catalog Lookup:** Handles direct, factual questions about the course catalog, such as course details, prerequisites, sections, instructors, and graduation requirements. It retrieves information without creating a personalized course or degree plan.

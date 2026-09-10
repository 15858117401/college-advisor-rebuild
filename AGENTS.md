# Project Instructions

- `college_advisor/` is the previous Java implementation. Do not inspect, modify, or use it unless the user explicitly asks for Java reference work.
- Write the new Python implementation in this repository root and its normal subdirectories, outside `college_advisor/`.
- Keep changes minimal. Do not add files, dependencies, configuration, or project structure unless the user explicitly asks for them.
- Place small local smoke or unit tests in `tests/`. These tests are for simple implementation verification, not evaluation or benchmark suites.
- Put evaluation assets in `Eval/`. This directory contains evaluation cases, manually labeled evaluation data, and the code used to run evaluation cases. Keep benchmark and prompt-evaluation work in `Eval/`, separate from the small implementation-verification tests in `tests/`.
- Put only agent-callable runtime tools in the lowercase `tools/` package, with their unit tests in `tests/` (for example, `tools/course_sections_tool.py` is tested by `tests/test_course_sections_tool.py`).
- Put all current and future Supabase-related code in `Supabase/`, including SQL schemas, migrations, database clients/helpers, validation scripts, and import/upload scripts. Never place this code in `tools/`; `tools/` is reserved exclusively for tools the advising agent can call at runtime.
- Advising supports all stored programs and course subjects (currently 61 program documents and 58 course subjects). Resolve programs from stored metadata; the major determines degree requirements, while relevant courses may come from any department. Do not add new resource imports, migrations, or embeddings without an explicit request.
- Section information is available only for the currently loaded semester, Spring 2026. Future-semester section data is unknown; do not infer or claim future course availability, CRNs, meeting times, locations, or instructors.
- Keep `graph.py` focused on graph assembly: node registration, edges, compilation, and exports. Do not place node business logic or LLM calls in it.
- Put each graph node implementation in its own module under the lowercase `nodes/` package.
- Centralize LLM initialization in `client/llm_client.py`. Nodes that need an LLM must import and reuse the shared `llm_client` instead of creating their own model client.
- `Resource/` stores course catalog, offering availability, and course/instructor GPA statistics used as reference data by the advising agent.
- Treat `graph.py` and the command-line evaluation runners as the current runtime surface. Do not expand the placeholder FastAPI app in `main.py` unless the user explicitly asks for API work.
- Skill loading is currently disabled for Catalog Lookup and Advising. Keep `CATALOG_SKILLS` and `ADVISING_SKILLS` empty unless the user explicitly starts a skill-integration task.


## Runtime Tools

The advising agents can call these tools from the lowercase `tools/` package:

- `get_course_details`: Retrieves catalog details for explicit UIUC course codes across stored subjects.
- `find_courses`: Finds courses across stored subjects with structured filters and optional semantic description matching. Optional `subjects` restricts departments; omission searches all stored subjects.
- `get_course_sections`: Retrieves Spring 2026 UIUC sections, CRNs, meeting times, locations, and instructors.
- `get_course_instructor_gpas`: Retrieves historical instructor average GPA statistics across stored subjects.
- `find_degree_programs`: Discovers stored program names, codes, document keys, types, and catalog years.
- `get_graduation_requirements`: Retrieves unchanged stored 2026–2027 requirement Markdown by exact program name, program code, or document key; `math` and `stats` remain aliases. Ambiguous requests return candidates. General-major documents do not replace missing concentration requirements, and Biology retains its redirect document.
- `search_rate_my_professor` and `search_reddit`: Search public professor ratings and student discussions through Tavily.

`nodes/catalog_lookup.py` owns the canonical `CATALOG_TOOLS` registration. Advising currently reuses that same list; adding a tool module alone does not make it agent-callable, so register new tools explicitly and add focused tests under `tests/`.


## Running and Evaluation

Run Python commands from the repository root with `.venv/bin/python`. The graph requires `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`. Supabase-backed tools require `SUPABASE_URL` and `SUPABASE_SECRET_KEY`; semantic course search additionally requires `OPENAI_API_KEY`, and professor research requires `TAVILY_API_KEY`.

```bash
# Focused graph and evaluation-runner verification
.venv/bin/python -m pytest -q tests/test_graph.py tests/test_run_full_eval.py tests/test_react_agent.py

# Live evaluations
.venv/bin/python Eval/router_eval/run_router_eval.py
.venv/bin/python Eval/run_full_eval.py --workers 5
```

The router runner overwrites `Eval/router_eval/router_cases_with_predictions.csv`. The full runner overwrites `Eval/full_eval_results.csv` and records `predicted_route` plus the final `response`; it does not generate a Markdown report. Both evaluation runners default to five concurrent cases and explicitly use `profile=None` for self-contained cases. Live evaluations use external services, so failures must distinguish code errors from credentials, rate limits, and transient network errors.


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

Apply `Supabase/stat_resource_schema.sql` for statistics resources and `Supabase/graduation_requirements_schema.sql` for graduation-requirement documents. The graduation importer reads `Resource/LASmajor_requirement/manifest.json` and verifies that the Markdown read back from Supabase exactly matches the local files. The broader course and instructor snapshot uses `Resource/las_course_catalog/` and `Resource/LASsectionGPA/`; preserve these resource paths. The current snapshot is already uploaded and embedded.


## Project Overview

This project rebuilds the college-advising agent in Python as a LangGraph workflow. `graph.py` defines node registration and transitions, `state.py` defines shared graph state, and `nodes/` contains the node implementations. The intended top-level business routes are Catalog Lookup, Advising, and Out of Scope. Clarify is a shared fallback state rather than a separate user intent.

Graph input must keep the current user input separate from prior conversation history. Store the current turn's raw user text in `current_input`; use the inherited `MessagesState.messages` container only for completed past messages. Nodes must not infer the current input from `messages[-1]`. The Router LLM call must send one structured user payload with separate `conversation_context` and `current_input` fields so the model never has to infer which message is current. ReAct nodes must use the shared `messages_with_current_input(...)` helper from `state.py` to assemble the temporary native chat history.

The saved profile is read-only. An explicit request or stated scenario takes precedence over conflicting profile facts for that answer. Never fill a different hypothetical student’s missing coursework or grades from the saved record. An explicit runtime context `{"profile": None}` disables the local-profile fallback; omitting `profile` preserves it. Retrieve the applicable stored requirements before building a degree plan, then check relevant courses across departments. Expected tool validation and unsupported-resource errors are recoverable tool messages; unexpected programming and service failures remain errors.

The currently wired flow is:

```text
START -> Router -> Planner -> Catalog Lookup -> Compose Response -> END
                           -> Advising       -> Compose Response -> END
                           -> Out of Scope   -> Compose Response -> END
                           -> Clarify        -> END
```

Router is the only node that writes `route`. Planner must preserve that value, and conditional route dispatch happens after Planner.

`nodes/clarify.py` is currently a placeholder that returns no state updates. The intended future behavior is still a shared missing-information fallback: any non-Clarify processing node may transition to Clarify, Clarify asks one question, and that graph run ends. Until that work is implemented, do not describe the fallback as complete and do not guess missing information merely to avoid it.

- **Router:** Classifies the user's request primarily as factual catalog lookup, personalized advising, or out of scope. It should only make a routing decision and should not answer the request, call business tools, or perform node business logic. Clarification is not a primary intent category, although Router may use the shared Clarify fallback if it cannot make a safe routing decision without additional user information.
- **Planner:** Runs immediately after Router and before route dispatch. For now it makes exactly one shared-LLM call with the system prompt `Do not do anything. Do not change anything.`, discards the model output, returns no state updates, and leaves Router's route decision unchanged. It must not perform planning, answer the user, or call business tools until explicitly expanded later.
- **Catalog Lookup:** Handles direct, factual questions about the course catalog, such as course details, prerequisites, sections, instructors, and graduation requirements. It retrieves information without creating a personalized course or degree plan, then sends its draft to Compose Response. Its Clarify transition is still future work.
- **Advising:** Handles personalized tasks whose results depend on the student's academic history, preferences, constraints, or goals, including course recommendations, schedule building, and degree planning. It currently reuses the factual tools registered by Catalog Lookup without calling the Catalog Lookup node itself. It normally sends a completed advising draft to Compose Response; its Clarify transition is still future work.
- **Clarify:** Is the planned shared missing-information fallback rather than a top-level business intent. Once implemented, it asks exactly one concise, targeted question and does no business work.
- **Compose Response:** Rewrites a completed draft from Catalog Lookup, Advising, or Out of Scope into a clear final answer while preserving its facts and conclusions and adding no new information. Its Clarify transition is still future work.
- **Out of Scope:** Writes the fixed draft `This is beyond the conversation` to shared response state, then sends it to Compose Response. It does not perform Catalog Lookup or Advising work; its Clarify transition is still future work.

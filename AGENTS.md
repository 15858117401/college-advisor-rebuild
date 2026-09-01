# Project Instructions

- `college_advisor/` is the previous Java implementation. Use it only as a read-only reference; do not modify it.
- Write the new Python implementation in this repository root and its normal subdirectories, outside `college_advisor/`.
- Keep changes minimal. Do not add files, dependencies, configuration, or project structure unless the user explicitly asks for them.
- Place small local smoke or unit tests in `tests/`. These tests are for simple implementation verification, not evaluation or benchmark suites.
- Put evaluation assets in `Eval/`. This directory contains evaluation cases, manually labeled evaluation data, and the code used to run evaluation cases. Keep benchmark and prompt-evaluation work in `Eval/`, separate from the small implementation-verification tests in `tests/`.
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

Apply `Supabase/stat_resource_schema.sql` for statistics resources and `Supabase/graduation_requirements_schema.sql` for graduation-requirement documents. The graduation importer reads `Resource/graduation_requirements/manifest.json`, uploads the Mathematics and Statistics major documents, and verifies that the Markdown read back from Supabase exactly matches the local files.


## Project Overview

This project rebuilds the college-advising agent in Python as a LangGraph workflow. `graph.py` defines node registration and transitions, `state.py` defines shared graph state, and `nodes/` contains the node implementations. The intended top-level business routes are Catalog Lookup, Advising, and Out of Scope. Clarify is a shared fallback state rather than a separate user intent.

Graph input must keep the current user input separate from prior conversation history. Store the current turn's raw user text in `current_input`; use the inherited `MessagesState.messages` container only for completed past messages. Nodes must not infer the current input from `messages[-1]`. The Router LLM call must send one structured user payload with separate `conversation_context` and `current_input` fields so the model never has to infer which message is current. ReAct nodes may assemble a temporary message list as `messages + current_input` when they need the native chat history format.

The intended flow is:

```text
START -> Router -> Catalog Lookup -> Compose Response -> END
                -> Advising       -> Compose Response -> END
                -> Out of Scope   -> Compose Response -> END

Any non-Clarify node -> Clarify -> END
```

After Clarify asks its question, the current graph run ends. The user's answer starts a new run at Router with the complete conversation history. Every non-Clarify processing node must be able to transition directly to Clarify whenever missing user-provided information prevents that node from safely continuing. Nodes must not guess missing information merely to avoid clarification.

- **Router:** Classifies the user's request primarily as factual catalog lookup, personalized advising, or out of scope. It should only make a routing decision and should not answer the request, call business tools, or perform node business logic. Clarification is not a primary intent category, although Router may use the shared Clarify fallback if it cannot make a safe routing decision without additional user information.
- **Catalog Lookup:** Handles direct, factual questions about the course catalog, such as course details, prerequisites, sections, instructors, and graduation requirements. It retrieves information without creating a personalized course or degree plan. It normally sends a completed factual draft to Compose Response, but it must transition to Clarify if the requested lookup cannot be identified safely from the available conversation.
- **Advising:** Handles personalized tasks whose results depend on the student's academic history, preferences, constraints, or goals, including course recommendations, schedule building, and degree planning. It may use advising-specific skills and tools, including factual course tools also used by Catalog Lookup, without calling the Catalog Lookup node itself. It normally sends a completed advising draft to Compose Response, but it must transition to Clarify when required student context is missing.
- **Clarify:** Is the shared missing-information fallback for every node, not a top-level business intent. It asks exactly one concise, targeted follow-up question based on the information the preceding node identified as missing. It does not answer the original request, perform business work, or invent a partial plan.
- **Compose Response:** Rewrites a completed draft from Catalog Lookup, Advising, or Out of Scope into a clear final answer while preserving its facts and conclusions and adding no new information. If it cannot safely produce a final response because required information is explicitly missing, it may transition to Clarify instead of filling the gap itself.
- **Out of Scope:** Writes the fixed draft `This is beyond the conversation` to the shared response state when a request falls outside supported college-advising capabilities, then sends that draft to Compose Response. It does not perform Catalog Lookup or Advising work. If the request's scope cannot be determined safely because essential context is missing, it may transition to Clarify.

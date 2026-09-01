# Repository Guidelines

## Project Structure & Module Organization

The Python advising workflow lives one level above this directory: `../graph.py` assembles the LangGraph, `../state.py` defines shared state, and each business node belongs in `../nodes/`. Agent-callable runtime tools live in `../tools/`; Supabase schemas and import utilities stay in `../Supabase/`. Treat `../college_advisor/` as read-only legacy reference material.

Keep benchmark assets in `Eval/`. Router cases, predictions, and the focused runner are under `router_eval/`; `run_full_eval.py` exercises the complete graph and writes each predicted route and final response to `full_eval_results.csv`. Small implementation tests belong in `../tests/`, while reference datasets belong in `../Resource/`.

## Build, Test, and Development Commands

Run commands from the repository root with the project virtual environment:

```bash
.venv/bin/python -m pytest tests
.venv/bin/python Eval/router_eval/run_router_eval.py
.venv/bin/python Eval/run_full_eval.py --workers 10
```

The first command runs local unit and smoke tests. The second evaluates router accuracy and writes a prediction CSV. The third runs full graph cases and generates a readable Markdown report. There is no separate build step.

## Coding Style & Naming Conventions

Use four-space indentation, PEP 8 naming, `snake_case` for functions and modules, and `UPPER_CASE` for constants. Add type hints to new public functions and use `pathlib.Path` for file paths. Keep graph assembly separate from node logic, and reuse the centralized `../llm_client.py` for LLM access. No formatter or linter is currently configured, so match nearby code and keep changes focused.

## Testing Guidelines

Use `pytest`. Name files `test_<module>.py` and tests `test_<behavior>()`. Add deterministic unit tests in `../tests/`; reserve CSV cases, labeled data, prompt comparisons, and generated benchmark reports for `Eval/`. Document any evaluation input or expected-label changes in the pull request.

## Commit & Pull Request Guidelines

Recent commits use short, implementation-focused summaries without mandatory prefixes. Write concise imperative subjects such as `Add router clarification cases`. Pull requests should explain the behavior changed, list tests or evaluations run, link relevant issues, and call out data or prompt changes. Include before/after metrics when evaluation behavior changes.

## Security & Configuration

Keep API keys and Supabase credentials in the uncommitted `.env`; never print them or place them in CSV reports. Evaluation scripts call live services, so choose worker counts with rate limits and cost in mind.

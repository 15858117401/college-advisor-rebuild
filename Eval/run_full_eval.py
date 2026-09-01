import argparse
import csv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph import graph


DEFAULT_INPUT = EVAL_DIR / "router_eval" / "router_cases_with_responses.csv"
DEFAULT_OUTPUT = EVAL_DIR / "full_eval_results.md"
DEFAULT_MAX_WORKERS = 10
MAX_ATTEMPTS_PER_CASE = 2


def run_case(user_query: str) -> tuple[str, str]:
    """Run one evaluation case through the complete advising graph."""
    for attempt in range(1, MAX_ATTEMPTS_PER_CASE + 1):
        try:
            result = graph.invoke(
                {
                    "current_input": user_query,
                    "messages": [],
                }
            )
            return str(result.get("route", "")), str(result.get("response", ""))
        except Exception:
            if attempt == MAX_ATTEMPTS_PER_CASE:
                raise

    raise AssertionError("unreachable")


def _blockquote(text: str) -> str:
    if not text:
        return "> _No content returned._"
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def _render_report(rows: list[dict[str, str]], workers: int) -> str:
    correct = sum(
        row["predicted_route"] == row["expected_route"] for row in rows
    )
    errors = sum(bool(row["error"]) for row in rows)
    accuracy = correct / len(rows) if rows else 0.0
    lines = [
        "# Full Graph Evaluation Results",
        "",
        f"- Cases: {len(rows)}",
        f"- Route matches: {correct}/{len(rows)} ({accuracy:.1%})",
        f"- Execution errors: {errors}",
        f"- Concurrency: {workers}",
        "",
    ]

    for row in rows:
        route_status = (
            "route matched"
            if row["predicted_route"] == row["expected_route"]
            else "route mismatch"
        )
        lines.extend(
            [
                f"## Case {row['case_id']} — {route_status}",
                "",
                f"- Expected route: `{row['expected_route']}`",
                f"- Actual route: `{row['predicted_route']}`",
                "",
                "### User query",
                "",
                _blockquote(row["user_query"]),
                "",
                "### Final response",
                "",
                _blockquote(row["response"]),
                "",
            ]
        )
        if row["error"]:
            lines.extend(
                [
                    "### Execution error",
                    "",
                    _blockquote(row["error"]),
                    "",
                ]
            )

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run every CSV case through the complete graph concurrently."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    return args


def main() -> None:
    args = parse_args()
    with args.input.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        source_rows = list(reader)
        fieldnames = set(reader.fieldnames or [])

    required_columns = {"case_id", "user_query", "expected_route"}
    missing_columns = required_columns.difference(fieldnames)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"missing required CSV columns: {missing}")

    rows = [
        {
            "case_id": row["case_id"],
            "user_query": row["user_query"],
            "expected_route": row["expected_route"],
            "predicted_route": "",
            "response": "",
            "error": "",
        }
        for row in source_rows
    ]

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_index = {
            executor.submit(run_case, row["user_query"]): index
            for index, row in enumerate(rows)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            row = rows[index]
            try:
                predicted_route, response = future.result()
                row["predicted_route"] = predicted_route
                row["response"] = response
            except Exception as exc:
                row["predicted_route"] = "error"
                row["error"] = f"{type(exc).__name__}: {exc}"

            completed += 1
            print(
                f"[{completed}/{len(rows)}] case={row['case_id']} "
                f"expected={row['expected_route']} "
                f"actual={row['predicted_route']}",
                flush=True,
            )

    report = _render_report(rows, args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")

    correct = sum(
        row["predicted_route"] == row["expected_route"] for row in rows
    )
    errors = sum(bool(row["error"]) for row in rows)
    accuracy = correct / len(rows) if rows else 0.0
    print(f"\nRoute matches: {correct}/{len(rows)} ({accuracy:.1%})")
    print(f"Execution errors: {errors}")
    print(f"Saved readable report to {args.output}")


if __name__ == "__main__":
    main()

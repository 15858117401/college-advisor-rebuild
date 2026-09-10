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
DEFAULT_OUTPUT = EVAL_DIR / "full_eval_results.csv"
DEFAULT_MAX_WORKERS = 5
MAX_ATTEMPTS_PER_CASE = 2


def run_case(user_query: str) -> tuple[str, str]:
    """Run one evaluation case through the complete advising graph."""
    for attempt in range(1, MAX_ATTEMPTS_PER_CASE + 1):
        try:
            result = graph.invoke(
                {
                    "current_input": user_query,
                    "messages": [],
                },
                context={"profile": None},
            )
            return str(result.get("route", "")), str(result.get("response", ""))
        except Exception:
            if attempt == MAX_ATTEMPTS_PER_CASE:
                raise

    raise AssertionError("unreachable")


def _print_final_results(rows: list[dict[str, str]]) -> None:
    print("\nFinal results:")
    for row in rows:
        print(
            f"\n=== Case {row['case_id']} ===\n"
            f"Expected route: {row['expected_route']}\n"
            f"Actual route: {row['predicted_route']}\n"
            f"User query: {row['user_query']}\n"
            f"Response:\n{row['response']}"
        )


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
        fieldnames = reader.fieldnames or []

    required_columns = {
        "case_id",
        "user_query",
        "expected_route",
        "predicted_route",
        "response",
    }
    missing_columns = required_columns.difference(set(fieldnames))
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"missing required CSV columns: {missing}")

    rows = [dict(row) for row in source_rows]
    for row in rows:
        row["predicted_route"] = ""
        row["response"] = ""

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
                row["response"] = f"ERROR: {type(exc).__name__}: {exc}"

            completed += 1
            print(
                f"[{completed}/{len(rows)}] case={row['case_id']} "
                f"expected={row['expected_route']} "
                f"actual={row['predicted_route']}",
                flush=True,
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    correct = sum(
        row["predicted_route"] == row["expected_route"] for row in rows
    )
    errors = sum(row["predicted_route"] == "error" for row in rows)
    accuracy = correct / len(rows) if rows else 0.0
    _print_final_results(rows)
    print(f"\nRoute matches: {correct}/{len(rows)} ({accuracy:.1%})")
    print(f"Execution errors: {errors}")
    print(f"Saved full results to {args.output}")


if __name__ == "__main__":
    main()

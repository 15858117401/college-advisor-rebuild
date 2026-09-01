import csv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nodes.router import router


INPUT_CSV = Path(__file__).with_name("router_cases_with_responses.csv")
OUTPUT_CSV = Path(__file__).with_name("router_cases_with_predictions.csv")
MAX_WORKERS = 10



def predict_route(user_query: str) -> str:
    result = router(
        {
            "current_input": user_query,
            "messages": [],
        }
    )
    return str(result["route"])


def main() -> None:
    with INPUT_CSV.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    required_columns = {"case_id", "user_query", "expected_route", "predicted_route"}
    missing_columns = required_columns.difference(fieldnames)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"missing required CSV columns: {missing}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_index = {
            executor.submit(predict_route, row["user_query"]): index
            for index, row in enumerate(rows)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            row = rows[index]
            try:
                row["predicted_route"] = future.result()
            except Exception as exc:
                row["predicted_route"] = f"ERROR: {type(exc).__name__}: {exc}"
            print(
                f"[{row['case_id']}] expected={row['expected_route']} "
                f"predicted={row['predicted_route']}",
                flush=True,
            )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    correct = sum(
        row["predicted_route"] == row["expected_route"] for row in rows
    )
    accuracy = correct / len(rows) if rows else 0.0
    print(f"\nAccuracy: {correct}/{len(rows)} ({accuracy:.1%})")
    print(f"Saved predictions to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

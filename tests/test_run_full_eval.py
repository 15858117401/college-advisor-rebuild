import argparse
import csv
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Eval import run_full_eval


FIELDNAMES = [
    "case_id",
    "user_query",
    "expected_route",
    "predicted_route",
    "route_label",
    "annotation_notes",
    "response",
]


class FullEvalTest(unittest.TestCase):
    def _write_input(self, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as destination:
            writer = csv.DictWriter(destination, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerow(
                {
                    "case_id": "1",
                    "user_query": "What is STAT 400?",
                    "expected_route": "catalog_lookup",
                    "predicted_route": "old-route",
                    "route_label": "keep-label",
                    "annotation_notes": "keep-notes",
                    "response": "old-response",
                }
            )

    def test_writes_full_graph_result_to_new_csv_and_preserves_input(self) -> None:
        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.csv"
            output_path = Path(temp_dir) / "output.csv"
            self._write_input(input_path)

            args = argparse.Namespace(
                input=input_path,
                output=output_path,
                workers=1,
            )
            with (
                patch.object(run_full_eval, "parse_args", return_value=args),
                patch.object(
                    run_full_eval,
                    "run_case",
                    return_value=("catalog_lookup", "Line one\nLine two"),
                ),
                patch("builtins.print") as print_mock,
            ):
                run_full_eval.main()

            with input_path.open(newline="", encoding="utf-8") as source:
                input_row = next(csv.DictReader(source))
            with output_path.open(newline="", encoding="utf-8") as source:
                output_row = next(csv.DictReader(source))

            self.assertEqual(input_row["predicted_route"], "old-route")
            self.assertEqual(input_row["response"], "old-response")
            self.assertEqual(output_row["predicted_route"], "catalog_lookup")
            self.assertEqual(output_row["response"], "Line one\nLine two")
            self.assertEqual(output_row["route_label"], "keep-label")
            self.assertEqual(output_row["annotation_notes"], "keep-notes")
            terminal_output = "\n".join(
                " ".join(str(arg) for arg in call.args)
                for call in print_mock.call_args_list
            )
            self.assertIn("=== Case 1 ===", terminal_output)
            self.assertIn("Line one\nLine two", terminal_output)

    def test_writes_case_error_to_response_column(self) -> None:
        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.csv"
            output_path = Path(temp_dir) / "output.csv"
            self._write_input(input_path)

            args = argparse.Namespace(
                input=input_path,
                output=output_path,
                workers=1,
            )
            with (
                patch.object(run_full_eval, "parse_args", return_value=args),
                patch.object(
                    run_full_eval,
                    "run_case",
                    side_effect=RuntimeError("service unavailable"),
                ),
            ):
                run_full_eval.main()

            with output_path.open(newline="", encoding="utf-8") as source:
                output_row = next(csv.DictReader(source))

            self.assertEqual(output_row["predicted_route"], "error")
            self.assertEqual(
                output_row["response"],
                "ERROR: RuntimeError: service unavailable",
            )




def test_full_runner_disables_local_profile():
    with patch.object(run_full_eval.graph, 'invoke', return_value={'route': 'advising', 'response': 'plan'}) as invoke:
        assert run_full_eval.run_case('Self-contained case') == ('advising', 'plan')
    assert invoke.call_args.kwargs['context'] == {'profile': None}


def test_router_runner_disables_local_profile():
    from Eval.router_eval import run_router_eval
    with patch.object(run_router_eval, 'router', return_value={'route': 'advising'}) as router:
        assert run_router_eval.predict_route('Self-contained case') == 'advising'
    assert router.call_args.kwargs['runtime'].context == {'profile': None}


def test_both_evaluation_runners_default_to_five_workers():
    from Eval.router_eval import run_router_eval
    with patch.object(sys, "argv", ["run_full_eval.py"]):
        assert run_full_eval.parse_args().workers == 5
    assert run_router_eval.MAX_WORKERS == 5


if __name__ == "__main__":
    unittest.main()

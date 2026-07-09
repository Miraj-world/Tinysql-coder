"""Evaluate generated SQL by running it against the real SQLite databases.

Exact string match is too strict for SQL. Execution evaluation checks whether
the predicted SQL returns the same rows as the gold SQL.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS_PATH = PROJECT_ROOT / "outputs" / "baseline" / "baseline_predictions.jsonl"
DATABASES_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "dev_databases"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "baseline"
OUTPUT_PATH = OUTPUT_DIR / "execution_eval.jsonl"
SUMMARY_PATH = OUTPUT_DIR / "execution_eval_summary.json"


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def sqlite_path_for_database(db_id: str) -> Path:
    sqlite_path = DATABASES_DIR / db_id / f"{db_id}.sqlite"

    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    return sqlite_path


def normalize_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)

    return value


def normalize_rows(rows: list[tuple]) -> list[list[Any]]:
    """Normalize result rows so ordering/float noise does not dominate scoring."""
    normalized_rows = [
        [normalize_value(value) for value in row]
        for row in rows
    ]
    return sorted(normalized_rows, key=lambda row: json.dumps(row, sort_keys=True, default=str))


def execute_sql(sqlite_path: Path, sql: str) -> dict:
    """Run SQL and capture either normalized rows or the execution error."""
    try:
        with sqlite3.connect(sqlite_path) as connection:
            cursor = connection.execute(sql)
            rows = cursor.fetchall()

        return {
            "ok": True,
            "rows": normalize_rows(rows),
            "error": None,
        }
    except Exception as error:
        return {
            "ok": False,
            "rows": None,
            "error": str(error),
        }


def evaluate_prediction(record: dict) -> dict:
    sqlite_path = sqlite_path_for_database(record["db_id"])
    gold_result = execute_sql(sqlite_path, record["expected_sql"])
    predicted_result = execute_sql(sqlite_path, record["predicted_sql"])

    execution_match = (
        gold_result["ok"]
        and predicted_result["ok"]
        and gold_result["rows"] == predicted_result["rows"]
    )

    return {
        "question_id": record["question_id"],
        "db_id": record["db_id"],
        "difficulty": record["difficulty"],
        "exact_match": record["exact_match"],
        "execution_match": execution_match,
        "gold_ok": gold_result["ok"],
        "predicted_ok": predicted_result["ok"],
        "gold_error": gold_result["error"],
        "predicted_error": predicted_result["error"],
        "gold_rows": gold_result["rows"],
        "predicted_rows": predicted_result["rows"],
        "expected_sql": record["expected_sql"],
        "predicted_sql": record["predicted_sql"],
    }


def build_summary(results: list[dict]) -> dict:
    total = len(results)
    exact_matches = sum(result["exact_match"] for result in results)
    execution_matches = sum(result["execution_match"] for result in results)
    predicted_execution_successes = sum(result["predicted_ok"] for result in results)
    gold_execution_successes = sum(result["gold_ok"] for result in results)

    return {
        "total": total,
        "exact_matches": exact_matches,
        "execution_matches": execution_matches,
        "gold_execution_successes": gold_execution_successes,
        "predicted_execution_successes": predicted_execution_successes,
    }


def parse_args() -> object:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate predicted SQL by executing it on SQLite databases.")
    parser.add_argument("--predictions-path", type=Path, default=PREDICTIONS_PATH)
    parser.add_argument("--output-path", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--summary-path", type=Path, default=SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    predictions = read_jsonl(args.predictions_path)
    results = [evaluate_prediction(record) for record in predictions]
    summary = build_summary(results)

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.summary_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_path, results)
    args.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Loaded predictions: {len(predictions)}")
    print(f"Wrote execution results to: {args.output_path}")
    print(f"Wrote summary to: {args.summary_path}")
    print()
    print(f"Exact matches: {summary['exact_matches']}/{summary['total']}")
    print(f"Execution matches: {summary['execution_matches']}/{summary['total']}")
    print(
        "Predicted SQL executed successfully: "
        f"{summary['predicted_execution_successes']}/{summary['total']}"
    )
    print(
        "Gold SQL executed successfully: "
        f"{summary['gold_execution_successes']}/{summary['total']}"
    )


if __name__ == "__main__":
    main()

"""Combine two prediction files using execution failure as a safe fallback signal."""

import argparse
import json
from pathlib import Path
from typing import Callable

from repair_sql_predictions import execute_sql


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def choose_prediction(
    primary: dict,
    fallback: dict,
    executor: Callable[[str, str], dict] = execute_sql,
) -> dict:
    if primary["question_id"] != fallback["question_id"]:
        raise ValueError("Primary and fallback question IDs do not match")
    if primary["db_id"] != fallback["db_id"]:
        raise ValueError("Primary and fallback database IDs do not match")
    if primary["expected_sql"] != fallback["expected_sql"]:
        raise ValueError("Primary and fallback gold SQL do not match")

    primary_result = executor(primary["db_id"], primary["predicted_sql"])
    use_fallback = not primary_result["ok"]
    selected = fallback if use_fallback else primary
    selected_sql = selected["predicted_sql"]

    return {
        **selected,
        "predicted_sql": selected_sql,
        "exact_match": selected_sql.strip() == selected["expected_sql"].strip(),
        "cascade_used_fallback": use_fallback,
        "cascade_primary_sql": primary["predicted_sql"],
        "cascade_fallback_sql": fallback["predicted_sql"],
        "cascade_primary_error": primary_result["error"],
    }


def build_cascade(
    primary_records: list[dict],
    fallback_records: list[dict],
    executor: Callable[[str, str], dict] = execute_sql,
) -> list[dict]:
    fallback_by_question = {record["question_id"]: record for record in fallback_records}
    if len(fallback_by_question) != len(fallback_records):
        raise ValueError("Fallback predictions contain duplicate question IDs")

    primary_ids = {record["question_id"] for record in primary_records}
    if primary_ids != set(fallback_by_question):
        raise ValueError("Primary and fallback prediction sets contain different questions")

    return [
        choose_prediction(record, fallback_by_question[record["question_id"]], executor)
        for record in primary_records
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Use fallback SQL only when primary SQL cannot execute.")
    parser.add_argument("--primary-path", type=Path, required=True)
    parser.add_argument("--fallback-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    primary_records = read_jsonl(args.primary_path)
    fallback_records = read_jsonl(args.fallback_path)
    cascade_records = build_cascade(primary_records, fallback_records)
    write_jsonl(args.output_path, cascade_records)

    fallback_count = sum(record["cascade_used_fallback"] for record in cascade_records)
    print(f"Primary predictions: {len(primary_records)}")
    print(f"Fallback predictions used: {fallback_count}")
    print(f"Wrote cascade predictions: {args.output_path}")


if __name__ == "__main__":
    main()

"""Select SQL by execution-result consensus without reading expected SQL."""

import argparse
import json
from pathlib import Path

try:
    from scripts.evaluate_sql_execution import execute_sql, sqlite_path_for_database
except ModuleNotFoundError:
    from evaluate_sql_execution import execute_sql, sqlite_path_for_database


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def result_fingerprint(rows: list[list]) -> str:
    return json.dumps(rows, sort_keys=True, ensure_ascii=False, default=str)


def consensus_index(results: list[dict], minimum_agreement: int = 2) -> tuple[int, int]:
    """Return selected index and agreement count; index zero is the safe default."""
    groups: dict[str, list[int]] = {}
    for index, result in enumerate(results):
        if not result["ok"] or not result["rows"]:
            continue
        groups.setdefault(result_fingerprint(result["rows"]), []).append(index)

    agreeing_groups = [indices for indices in groups.values() if len(indices) >= minimum_agreement]
    if not agreeing_groups:
        return 0, 1
    agreeing_groups.sort(key=lambda indices: (-len(indices), indices[0]))
    winner = agreeing_groups[0]
    return winner[0], len(winner)


def build_consensus(prediction_sets: list[list[dict]], minimum_agreement: int = 2) -> list[dict]:
    primary = prediction_sets[0]
    indexed_sets = [
        {record["question_id"]: record for record in records}
        for records in prediction_sets
    ]
    expected_ids = {record["question_id"] for record in primary}
    if any(set(records) != expected_ids for records in indexed_sets):
        raise ValueError("Prediction sets contain different question IDs")

    selected_records = []
    for primary_record in primary:
        question_id = primary_record["question_id"]
        candidates = [records[question_id] for records in indexed_sets]
        if any(candidate["db_id"] != primary_record["db_id"] for candidate in candidates):
            raise ValueError(f"Database mismatch for question {question_id}")
        sqlite_path = sqlite_path_for_database(primary_record["db_id"])
        results = [execute_sql(sqlite_path, candidate["predicted_sql"]) for candidate in candidates]
        selected_index, agreement = consensus_index(results, minimum_agreement)
        selected = candidates[selected_index]
        selected_records.append(
            {
                **selected,
                "consensus_selected_index": selected_index,
                "consensus_agreement": agreement,
                "consensus_primary_sql": primary_record["predicted_sql"],
            }
        )
    return selected_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Choose SQL by non-empty execution consensus.")
    parser.add_argument("--prediction-path", type=Path, action="append", required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--minimum-agreement", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.prediction_path) < 2:
        raise ValueError("Provide at least two --prediction-path inputs")
    prediction_sets = [read_jsonl(path) for path in args.prediction_path]
    records = build_consensus(prediction_sets, args.minimum_agreement)
    write_jsonl(args.output_path, records)
    changed = sum(record["consensus_selected_index"] != 0 for record in records)
    print(f"Prediction sets: {len(prediction_sets)}")
    print(f"Predictions changed by consensus: {changed}/{len(records)}")
    print(f"Wrote: {args.output_path}")


if __name__ == "__main__":
    main()

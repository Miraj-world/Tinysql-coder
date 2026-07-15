"""Build gold-free prompts for selecting among executable SQL candidates."""

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


def candidate_section(candidates: list[dict], max_candidates: int = 8) -> str:
    seen_sql = set()
    lines = []
    for candidate in candidates:
        sql = candidate["sql"].strip()
        normalized = " ".join(sql.casefold().split())
        if normalized in seen_sql or not candidate["result"]["ok"]:
            continue
        seen_sql.add(normalized)
        rows = candidate["result"]["rows"]
        sample = json.dumps(rows[:2], ensure_ascii=False, default=str)
        if len(sample) > 300:
            sample = sample[:297] + "..."
        number = len(lines) + 1
        lines.append(
            f"Candidate {number}:\n{sql}\n"
            f"Returned rows: {len(rows)}; sample: {sample}"
        )
        if len(lines) >= max_candidates:
            break
    return "\n\n".join(lines)


def judge_prompt(original_prompt: str, section: str) -> str:
    marker = "\n\nReturn only the SQL query."
    if marker not in original_prompt:
        raise ValueError("Prompt does not contain the SQL return instruction")
    instruction = (
        "\n\nSeveral candidate queries executed successfully. Choose the candidate whose "
        "columns, joins, filters, aggregation, and returned rows best answer the question. "
        "Do not invent extra conditions.\n\n"
        + section
    )
    return original_prompt.replace(marker, instruction + marker, 1)


def build_judge_records(
    eval_records: list[dict],
    prediction_sets: list[list[dict]],
    max_candidates: int = 8,
) -> list[dict]:
    indexed_sets = [
        {record["question_id"]: record for record in records}
        for records in prediction_sets
    ]
    output = []
    for record in eval_records:
        question_id = record["question_id"]
        sqlite_path = sqlite_path_for_database(record["db_id"])
        candidates = []
        for indexed in indexed_sets:
            prediction = indexed[question_id]
            candidates.append(
                {
                    "sql": prediction["predicted_sql"],
                    "result": execute_sql(sqlite_path, prediction["predicted_sql"]),
                }
            )
        section = candidate_section(candidates, max_candidates)
        output.append(
            {
                **record,
                "prompt": judge_prompt(record["prompt"], section),
                "prompt_style": "sql_candidate_judge_v1",
                "judge_candidate_count": section.count("Candidate "),
            }
        )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build executable-candidate SQL judge prompts.")
    parser.add_argument("--eval-set-path", type=Path, required=True)
    parser.add_argument("--prediction-path", type=Path, action="append", required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--max-candidates", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    eval_records = read_jsonl(args.eval_set_path)
    prediction_sets = [read_jsonl(path) for path in args.prediction_path]
    records = build_judge_records(eval_records, prediction_sets, args.max_candidates)
    write_jsonl(args.output_path, records)
    print(f"Records: {len(records)}")
    print(f"Average candidates: {sum(r['judge_candidate_count'] for r in records) / len(records):.2f}")
    print(f"Wrote: {args.output_path}")


if __name__ == "__main__":
    main()

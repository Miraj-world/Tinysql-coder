"""Inspect execution-matched predictions from an evaluation run.

When a run improves, we should inspect what worked. This script extracts the
successful examples so we can learn which patterns the model is starting to
handle.
"""

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_PATH = PROJECT_ROOT / "outputs" / "lora-run-003" / "execution_eval.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "analysis" / "lora-run-003-successes.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect SQL predictions that matched by execution.")
    parser.add_argument("--eval-path", type=Path, default=DEFAULT_EVAL_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def sql_block(sql: str) -> str:
    return f"```sql\n{sql.strip()}\n```"


def has_join(sql: str) -> bool:
    return " join " in f" {sql.lower()} "


def build_report(records: list[dict]) -> str:
    successes = [record for record in records if record["execution_match"]]

    lines = [
        "# Successful Prediction Inspection",
        "",
        f"Execution matches: {len(successes)}/{len(records)}",
        "",
        "## Summary",
        "",
        f"Successful predictions using joins: {sum(has_join(record['predicted_sql']) for record in successes)}",
        f"Gold SQL using joins: {sum(has_join(record['expected_sql']) for record in successes)}",
        "",
    ]

    if not successes:
        lines.append("No execution-matched predictions found.")
        return "\n".join(lines)

    lines.append("## Successful Examples")
    lines.append("")

    for record in successes:
        lines.extend(
            [
                f"### Question {record['question_id']}",
                "",
                f"- Database: `{record['db_id']}`",
                f"- Difficulty: `{record['difficulty']}`",
                f"- Predicted SQL uses join: `{has_join(record['predicted_sql'])}`",
                f"- Gold SQL uses join: `{has_join(record['expected_sql'])}`",
                "",
                "**Predicted SQL**",
                "",
                sql_block(record["predicted_sql"]),
                "",
                "**Gold SQL**",
                "",
                sql_block(record["expected_sql"]),
                "",
                "**Returned Rows**",
                "",
                "```json",
                json.dumps(record["predicted_rows"], indent=2, ensure_ascii=False),
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    records = read_jsonl(args.eval_path)
    report = build_report(records)

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(report, encoding="utf-8")

    successes = [record for record in records if record["execution_match"]]
    print(f"Loaded examples: {len(records)}")
    print(f"Execution matches: {len(successes)}")
    print(f"Wrote success report: {args.output_path}")


if __name__ == "__main__":
    main()

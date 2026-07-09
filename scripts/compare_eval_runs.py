"""Compare two execution-evaluation JSONL files side by side.

This is a human-inspection tool, not a model-training script. It helps us see
whether a new run improved, regressed, or failed for the same reasons as the
baseline.
"""

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEFT_PATH = PROJECT_ROOT / "outputs" / "baseline" / "execution_eval.jsonl"
DEFAULT_RIGHT_PATH = PROJECT_ROOT / "outputs" / "lora-run-001" / "execution_eval.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "comparisons" / "base-vs-lora-run-001.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two SQL execution-evaluation runs.")
    parser.add_argument("--left-path", type=Path, default=DEFAULT_LEFT_PATH)
    parser.add_argument("--right-path", type=Path, default=DEFAULT_RIGHT_PATH)
    parser.add_argument("--left-name", default="Base Qwen")
    parser.add_argument("--right-name", default="LoRA Run 001")
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--max-examples", type=int, default=20)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def index_by_question_id(records: list[dict]) -> dict[int, dict]:
    return {record["question_id"]: record for record in records}


def summarize(records: list[dict]) -> dict:
    total = len(records)
    return {
        "total": total,
        "exact_matches": sum(record["exact_match"] for record in records),
        "execution_matches": sum(record["execution_match"] for record in records),
        "predicted_ok": sum(record["predicted_ok"] for record in records),
        "gold_ok": sum(record["gold_ok"] for record in records),
    }


def status_label(record: dict) -> str:
    if record["execution_match"]:
        return "execution_match"
    if record["predicted_ok"]:
        return "executes_wrong_result"
    return "execution_error"


def sql_block(sql: str) -> str:
    return f"```sql\n{sql.strip()}\n```"


def build_markdown(
    left_records: list[dict],
    right_records: list[dict],
    left_name: str,
    right_name: str,
    max_examples: int,
) -> str:
    left_by_id = index_by_question_id(left_records)
    right_by_id = index_by_question_id(right_records)
    shared_question_ids = [
        question_id
        for question_id in left_by_id
        if question_id in right_by_id
    ]

    left_summary = summarize(left_records)
    right_summary = summarize(right_records)

    lines = [
        "# Evaluation Run Comparison",
        "",
        "## Summary",
        "",
        "| Run | Total | Exact | Execution Match | Predicted SQL Executes | Gold SQL Executes |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| {left_name} | {left_summary['total']} | {left_summary['exact_matches']} | "
            f"{left_summary['execution_matches']} | {left_summary['predicted_ok']} | {left_summary['gold_ok']} |"
        ),
        (
            f"| {right_name} | {right_summary['total']} | {right_summary['exact_matches']} | "
            f"{right_summary['execution_matches']} | {right_summary['predicted_ok']} | {right_summary['gold_ok']} |"
        ),
        "",
        "## Per-Question Comparison",
        "",
    ]

    for question_id in shared_question_ids[:max_examples]:
        left = left_by_id[question_id]
        right = right_by_id[question_id]

        lines.extend(
            [
                f"### Question {question_id}",
                "",
                f"- Database: `{left['db_id']}`",
                f"- Difficulty: `{left['difficulty']}`",
                f"- {left_name}: `{status_label(left)}`",
                f"- {right_name}: `{status_label(right)}`",
                "",
                f"**{left_name} predicted SQL**",
                "",
                sql_block(left["predicted_sql"]),
                "",
                f"Error: `{left['predicted_error']}`" if left["predicted_error"] else "Error: `none`",
                "",
                f"**{right_name} predicted SQL**",
                "",
                sql_block(right["predicted_sql"]),
                "",
                f"Error: `{right['predicted_error']}`" if right["predicted_error"] else "Error: `none`",
                "",
                "**Gold SQL**",
                "",
                sql_block(left["expected_sql"]),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    left_records = read_jsonl(args.left_path)
    right_records = read_jsonl(args.right_path)

    markdown = build_markdown(
        left_records=left_records,
        right_records=right_records,
        left_name=args.left_name,
        right_name=args.right_name,
        max_examples=args.max_examples,
    )

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(markdown, encoding="utf-8")

    print(f"Compared {args.left_name} vs {args.right_name}")
    print(f"Left: {args.left_path}")
    print(f"Right: {args.right_path}")
    print(f"Wrote comparison report: {args.output_path}")


if __name__ == "__main__":
    main()

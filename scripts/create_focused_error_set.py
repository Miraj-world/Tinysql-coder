"""Create a focused error set for the next SQL repair experiment.

The broad failure reports are useful, but they mix two different problems:

1. SQL that is mechanically broken and might be safe to repair after generation.
2. SQL that runs but answers the wrong question and probably needs better model
   behavior, not a string rewrite.

This script keeps the first group visible. It reads one or more execution eval
JSONL files, classifies each failed prediction with the existing failure
classifier, and writes a compact JSONL plus a markdown report.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_failure_patterns import classify_record, sql_block


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_PATHS = [
    PROJECT_ROOT / "outputs" / "lora-run-004-table-repaired" / "execution_eval.jsonl",
    PROJECT_ROOT / "outputs" / "lora-run-007-repaired" / "execution_eval.jsonl",
    PROJECT_ROOT / "outputs" / "lora-run-008-repaired" / "execution_eval.jsonl",
]
DEFAULT_JSONL_PATH = PROJECT_ROOT / "outputs" / "analysis" / "focused-repair-error-set.jsonl"
DEFAULT_MARKDOWN_PATH = PROJECT_ROOT / "outputs" / "analysis" / "focused-repair-error-set.md"
DEFAULT_TARGET_CATEGORIES = {
    "wrong_table_for_column",
    "ambiguous_or_unqualified_column",
    "execution_error_other",
    "invented_column",
    "hallucinated_table",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a focused SQL repair error set.")
    parser.add_argument(
        "--eval-path",
        type=Path,
        action="append",
        default=None,
        help="Execution eval JSONL path. Can be passed multiple times.",
    )
    parser.add_argument("--jsonl-output", type=Path, default=DEFAULT_JSONL_PATH)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument(
        "--category",
        action="append",
        default=None,
        help="Failure category to include. Can be passed multiple times.",
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def run_name_from_eval_path(path: Path) -> str:
    parts = path.parts
    try:
        outputs_index = parts.index("outputs")
        return parts[outputs_index + 1]
    except (ValueError, IndexError):
        return path.parent.name


def focused_rows(eval_paths: list[Path], target_categories: set[str]) -> list[dict]:
    schema_cache: dict[str, dict[str, set[str]]] = {}
    rows: list[dict] = []

    for eval_path in eval_paths:
        run_name = run_name_from_eval_path(eval_path)
        for record in read_jsonl(eval_path):
            category, detail = classify_record(record, schema_cache)
            if category not in target_categories:
                continue

            rows.append(
                {
                    "run_name": run_name,
                    "question_id": record["question_id"],
                    "db_id": record["db_id"],
                    "difficulty": record["difficulty"],
                    "category": category,
                    "detail": detail,
                    "predicted_error": record["predicted_error"],
                    "predicted_sql": record["predicted_sql"],
                    "expected_sql": record["expected_sql"],
                }
            )

    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        for row in rows:
            output_file.write(json.dumps(row, ensure_ascii=True) + "\n")


def build_markdown(rows: list[dict], eval_paths: list[Path], target_categories: set[str]) -> str:
    category_counts = Counter(row["category"] for row in rows)
    run_counts = Counter(row["run_name"] for row in rows)
    pair_counts = Counter((row["run_name"], row["category"]) for row in rows)

    lines = [
        "# Focused SQL Repair Error Set",
        "",
        "This report filters evaluation failures down to cases that might be useful",
        "for a guarded post-generation SQL repair pass.",
        "",
        "It intentionally excludes `executes_wrong_result` because those failures",
        "usually need better query reasoning, not a mechanical syntax or schema fix.",
        "",
        "## Inputs",
        "",
    ]

    for eval_path in eval_paths:
        lines.append(f"- `{eval_path.relative_to(PROJECT_ROOT)}`")

    lines.extend(
        [
            "",
            "## Included Categories",
            "",
        ]
    )
    for category in sorted(target_categories):
        lines.append(f"- `{category}`")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"Focused examples: {len(rows)}",
            "",
            "| Category | Count |",
            "|---|---:|",
        ]
    )
    for category, count in category_counts.most_common():
        lines.append(f"| `{category}` | {count} |")

    lines.extend(["", "| Run | Count |", "|---|---:|"])
    for run_name, count in run_counts.most_common():
        lines.append(f"| `{run_name}` | {count} |")

    lines.extend(["", "| Run | Category | Count |", "|---|---|---:|"])
    for (run_name, category), count in sorted(pair_counts.items()):
        lines.append(f"| `{run_name}` | `{category}` | {count} |")

    lines.extend(
        [
            "",
            "## Examples",
            "",
        ]
    )

    for row in rows:
        lines.extend(
            [
                f"### {row['run_name']} / Question {row['question_id']}",
                "",
                f"- Database: `{row['db_id']}`",
                f"- Difficulty: `{row['difficulty']}`",
                f"- Category: `{row['category']}`",
                f"- Detail: {row['detail']}",
                "",
                "**Predicted SQL**",
                "",
                sql_block(row["predicted_sql"]),
                "",
                "**Gold SQL**",
                "",
                sql_block(row["expected_sql"]),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    eval_paths = args.eval_path or DEFAULT_EVAL_PATHS
    target_categories = set(args.category or DEFAULT_TARGET_CATEGORIES)

    rows = focused_rows(eval_paths, target_categories)
    write_jsonl(args.jsonl_output, rows)

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(
        build_markdown(rows, eval_paths, target_categories),
        encoding="utf-8",
    )

    print(f"Focused examples: {len(rows)}")
    for category, count in Counter(row["category"] for row in rows).most_common():
        print(f"{category}: {count}")
    print(f"Wrote JSONL: {args.jsonl_output}")
    print(f"Wrote markdown: {args.markdown_output}")


if __name__ == "__main__":
    main()

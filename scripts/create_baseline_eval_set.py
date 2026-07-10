"""Create a small fixed validation sample for baseline experiments.

The same 20 examples are reused across prompt/model changes so we can compare
before and after results without changing the test set underneath ourselves.
"""

import json
import random
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VALIDATION_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed" / "validation.jsonl"
SCHEMA_GUIDANCE_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema" / "schema_guidance.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "baseline"
OUTPUT_PATH = OUTPUT_DIR / "baseline_eval_set.jsonl"

SAMPLE_SIZE = 20
RANDOM_SEED = 42

SCHEMA_GROUNDING_RULES = """Before writing SQL:
1. Use only tables and columns listed in the schema.
2. Do not use the database ID as a table name.
3. If the question needs columns from multiple tables, join the tables using shared key columns.
4. If a column is not in a table, do not reference it from that table."""

OWNERSHIP_TEACHER_RULES = """Before writing SQL:
1. Identify each important column and the table that owns it.
2. Identify the join keys needed to connect those tables.
3. Do not place a column on a table unless that column is listed under that table.
4. End with FINAL_SQL: followed by only the SQL query."""

ERROR_AWARE_RULES = """Before writing SQL:
1. Choose PLAN_TYPE: local_schema_fix, lookup_or_value_fix, fact_table_first, or fresh_query_plan.
2. Use local_schema_fix only for simple column/table ownership issues.
3. Use fact_table_first when the question is really about events, matches, transactions, results, or other fact rows.
4. Use fresh_query_plan when the question needs a subquery, date transform, UNION, CTE, or multi-step aggregation.
5. End with FINAL_SQL: followed by only the SQL query."""


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:    
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def build_prompt(example: dict) -> str:
    """Build the exact prompt sent to the base model during baseline runs."""
    return "\n\n".join(
        [
            example["instruction"],
            SCHEMA_GROUNDING_RULES,
            example["input"],
            "Return only the SQL query.",
        ]
    )


def build_ownership_teacher_prompt(example: dict, schema_guidance_by_db: dict[str, str]) -> str:
    db_id = example["metadata"]["db_id"]
    schema_guidance = schema_guidance_by_db.get(db_id)
    if schema_guidance is None:
        raise KeyError(f"No schema guidance found for db_id: {db_id}")

    return "\n\n".join(
        [
            example["instruction"],
            OWNERSHIP_TEACHER_RULES,
            "Schema guidance:",
            schema_guidance,
            example["input"],
        ]
    )


def build_error_aware_prompt(example: dict, schema_guidance_by_db: dict[str, str]) -> str:
    db_id = example["metadata"]["db_id"]
    schema_guidance = schema_guidance_by_db.get(db_id)
    if schema_guidance is None:
        raise KeyError(f"No schema guidance found for db_id: {db_id}")

    return "\n\n".join(
        [
            example["instruction"],
            ERROR_AWARE_RULES,
            "Schema guidance:",
            schema_guidance,
            example["input"],
        ]
    )


def choose_balanced_sample(examples: list[dict]) -> list[dict]:
    random_generator = random.Random(RANDOM_SEED)
    grouped_examples = defaultdict(list)

    for example in examples:
        difficulty = example.get("metadata", {}).get("difficulty", "unknown")
        grouped_examples[difficulty].append(example)

    for group in grouped_examples.values():
        random_generator.shuffle(group)

    selected = []
    difficulty_names = sorted(grouped_examples)

    while len(selected) < SAMPLE_SIZE and any(grouped_examples.values()):
        for difficulty in difficulty_names:
            if len(selected) >= SAMPLE_SIZE:
                break
            if grouped_examples[difficulty]:
                selected.append(grouped_examples[difficulty].pop())

    random_generator.shuffle(selected)
    return selected


def create_eval_record(
    example: dict,
    prompt_style: str,
    schema_guidance_by_db: dict[str, str],
) -> dict:
    metadata = example["metadata"]
    if prompt_style == "ownership_teacher_v5":
        prompt = build_ownership_teacher_prompt(example, schema_guidance_by_db)
    elif prompt_style == "error_aware_v6":
        prompt = build_error_aware_prompt(example, schema_guidance_by_db)
    else:
        prompt = build_prompt(example)

    return {
        "question_id": metadata["question_id"],
        "db_id": metadata["db_id"],
        "difficulty": metadata["difficulty"],
        "prompt": prompt,
        "prompt_style": prompt_style,
        "expected_sql": example["output"],
    }


def parse_args() -> object:
    import argparse

    parser = argparse.ArgumentParser(description="Create a fixed 20-example SQL evaluation set.")
    parser.add_argument(
        "--prompt-style",
        choices=["baseline", "ownership_teacher_v5", "error_aware_v6"],
        default="baseline",
    )
    parser.add_argument("--output-path", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validation_examples = read_jsonl(VALIDATION_PATH)
    schema_guidance_by_db = read_json(SCHEMA_GUIDANCE_PATH)
    sample = choose_balanced_sample(validation_examples)
    eval_records = [
        create_eval_record(example, args.prompt_style, schema_guidance_by_db)
        for example in sample
    ]

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_path, eval_records)

    difficulty_counts = Counter(record["difficulty"] for record in eval_records)

    print(f"Loaded validation examples: {len(validation_examples)}")
    print(f"Prompt style: {args.prompt_style}")
    print(f"Wrote eval set: {args.output_path}")
    print(f"Baseline sample size: {len(eval_records)}")
    print("Difficulty counts:")
    for difficulty, count in sorted(difficulty_counts.items()):
        print(f"  {difficulty}: {count}")
    print("\nFirst prompt:")
    print(eval_records[0]["prompt"])
    print("\nExpected SQL:")
    print(eval_records[0]["expected_sql"])


if __name__ == "__main__":
    main()

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
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "baseline"
OUTPUT_PATH = OUTPUT_DIR / "baseline_eval_set.jsonl"

SAMPLE_SIZE = 20
RANDOM_SEED = 42

SCHEMA_GROUNDING_RULES = """Before writing SQL:
1. Use only tables and columns listed in the schema.
2. Do not use the database ID as a table name.
3. If the question needs columns from multiple tables, join the tables using shared key columns.
4. If a column is not in a table, do not reference it from that table."""


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


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


def create_eval_record(example: dict) -> dict:
    metadata = example["metadata"]
    return {
        "question_id": metadata["question_id"],
        "db_id": metadata["db_id"],
        "difficulty": metadata["difficulty"],
        "prompt": build_prompt(example),
        "expected_sql": example["output"],
    }


def main() -> None:
    validation_examples = read_jsonl(VALIDATION_PATH)
    sample = choose_balanced_sample(validation_examples)
    eval_records = [create_eval_record(example) for example in sample]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUTPUT_PATH, eval_records)

    difficulty_counts = Counter(record["difficulty"] for record in eval_records)

    print(f"Loaded validation examples: {len(validation_examples)}")
    print(f"Wrote baseline eval set: {OUTPUT_PATH}")
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

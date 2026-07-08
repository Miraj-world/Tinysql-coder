import json
from pathlib import Path

from datasets import Dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATASET_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "raw" / "bird-original.arrow"
OUTPUT_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed"
OUTPUT_PATH = OUTPUT_DIR / "training_data.jsonl"

INSTRUCTION = "Convert the database question into a valid SQL query."


def build_input(row: dict) -> str:
    parts = [
        f"Database ID: {row['db_id']}",
        f"Question: {row['question']}",
    ]

    if row.get("evidence"):
        parts.append(f"Evidence: {row['evidence']}")

    return "\n".join(parts)


def convert_row(row: dict) -> dict:
    return {
        "instruction": INSTRUCTION,
        "input": build_input(row),
        "output": row["SQL"],
        "metadata": {
            "question_id": row["question_id"],
            "db_id": row["db_id"],
            "difficulty": row["difficulty"],
        },
    }


def prepare_training_data() -> None:
    dataset = Dataset.from_file(str(RAW_DATASET_PATH))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for row in dataset:
            example = convert_row(row)
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")

    print(f"Loaded {len(dataset)} rows from {RAW_DATASET_PATH}")
    print(f"Wrote training examples to {OUTPUT_PATH}")
    print("\nFirst example:")
    print(json.dumps(convert_row(dataset[0]), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    prepare_training_data()

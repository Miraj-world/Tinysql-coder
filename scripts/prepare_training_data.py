"""Convert raw BIRD rows into our project training format.

This step combines each question/SQL row with its matching database schema.
The result is still a general JSONL format, not yet the chat-style SFT format.
"""

import json
from pathlib import Path

from datasets import Dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATASET_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "raw" / "bird-original.arrow"
SCHEMA_TEXT_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema" / "schema_text.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed"
OUTPUT_PATH = OUTPUT_DIR / "training_data.jsonl"

INSTRUCTION = "Convert the database question into a valid SQL query."


def load_schema_text() -> dict[str, str]:
    """Load compact table(column, ...) schema text for each database ID."""
    if not SCHEMA_TEXT_PATH.exists():
        raise FileNotFoundError(
            f"Schema text not found at {SCHEMA_TEXT_PATH}. "
            "Run scripts/extract_schema_text.py first."
        )

    return json.loads(SCHEMA_TEXT_PATH.read_text(encoding="utf-8"))


def build_input(row: dict, schema_by_database: dict[str, str]) -> str:
    """Build the user-visible input: database ID, schema, question, evidence."""
    db_id = row["db_id"]
    schema_text = schema_by_database.get(db_id)

    if not schema_text:
        raise KeyError(f"No schema text found for database ID: {db_id}")

    parts = [
        f"Database ID: {db_id}",
        f"Schema:\n{schema_text}",
        f"Question: {row['question']}",
    ]

    if row.get("evidence"):
        parts.append(f"Evidence: {row['evidence']}")

    return "\n".join(parts)


def convert_row(row: dict, schema_by_database: dict[str, str]) -> dict:
    """Convert one raw dataset row into instruction/input/output format."""
    return {
        "instruction": INSTRUCTION,
        "input": build_input(row, schema_by_database),
        "output": row["SQL"],
        "metadata": {
            "question_id": row["question_id"],
            "db_id": row["db_id"],
            "difficulty": row["difficulty"],
        },
    }


def prepare_training_data() -> None:
    """Write all processed examples to data/bird_mini_dev/processed."""
    dataset = Dataset.from_file(str(RAW_DATASET_PATH))
    schema_by_database = load_schema_text()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for row in dataset:
            example = convert_row(row, schema_by_database)
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")

    print(f"Loaded {len(dataset)} rows from {RAW_DATASET_PATH}")
    print(f"Wrote training examples to {OUTPUT_PATH}")
    print("\nFirst example:")
    print(json.dumps(convert_row(dataset[0], schema_by_database), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    prepare_training_data()

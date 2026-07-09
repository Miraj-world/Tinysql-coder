"""Convert processed examples into chat-style supervised fine-tuning data.

SFT examples use system/user/assistant messages. The assistant message is the
gold SQL, which teaches the model the target response format.
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed"
SFT_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft"

TRAIN_INPUT_PATH = PROCESSED_DIR / "train.jsonl"
VALIDATION_INPUT_PATH = PROCESSED_DIR / "validation.jsonl"
TRAIN_OUTPUT_PATH = SFT_DIR / "train_sft.jsonl"
VALIDATION_OUTPUT_PATH = SFT_DIR / "validation_sft.jsonl"

SYSTEM_MESSAGE = (
    "You are a careful text-to-SQL assistant. "
    "Use only the provided schema. Return only the SQL query."
)

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


def build_user_message(example: dict) -> str:
    """Create the user message containing rules, schema, question, and evidence."""
    return "\n\n".join(
        [
            example["instruction"],
            SCHEMA_GROUNDING_RULES,
            example["input"],
        ]
    )


def convert_to_sft_example(example: dict) -> dict:
    """Wrap one processed example in chat messages for SFT training."""
    return {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            },
            {
                "role": "user",
                "content": build_user_message(example),
            },
            {
                "role": "assistant",
                "content": example["output"],
            },
        ],
        "metadata": example["metadata"],
    }


def convert_file(input_path: Path, output_path: Path) -> list[dict]:
    examples = read_jsonl(input_path)
    sft_examples = [convert_to_sft_example(example) for example in examples]
    write_jsonl(output_path, sft_examples)
    return sft_examples


def main() -> None:
    SFT_DIR.mkdir(parents=True, exist_ok=True)

    train_examples = convert_file(TRAIN_INPUT_PATH, TRAIN_OUTPUT_PATH)
    validation_examples = convert_file(VALIDATION_INPUT_PATH, VALIDATION_OUTPUT_PATH)

    print(f"Wrote train SFT examples: {len(train_examples)} -> {TRAIN_OUTPUT_PATH}")
    print(f"Wrote validation SFT examples: {len(validation_examples)} -> {VALIDATION_OUTPUT_PATH}")
    print("\nFirst train SFT example:")
    print(json.dumps(train_examples[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

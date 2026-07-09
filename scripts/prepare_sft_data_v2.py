"""Prepare Run 002 SFT data with explicit schema-grounding guidance.

Run 001 used schema text, but failure analysis showed many wrong-table-column
errors. This V2 format adds a dedicated schema guidance section so the prompt
teaches table-column ownership and likely join keys more directly.
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed"
SCHEMA_GUIDANCE_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema" / "schema_guidance.json"
SFT_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft_v2"

TRAIN_INPUT_PATH = PROCESSED_DIR / "train.jsonl"
VALIDATION_INPUT_PATH = PROCESSED_DIR / "validation.jsonl"
TRAIN_OUTPUT_PATH = SFT_DIR / "train_sft_v2.jsonl"
VALIDATION_OUTPUT_PATH = SFT_DIR / "validation_sft_v2.jsonl"

SYSTEM_MESSAGE = (
    "You are a careful text-to-SQL assistant. "
    "Use only the provided schema and schema guidance. Return only the SQL query."
)

SCHEMA_GROUNDING_RULES = """Before writing SQL:
1. First identify which table owns each needed column.
2. Use table aliases only after choosing the correct source table.
3. Join tables using shared key columns from the schema guidance.
4. Do not place a column on a table unless that column is listed under that table.
5. Return only the final SQL query."""


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_user_message(example: dict, schema_guidance_by_db: dict[str, str]) -> str:
    db_id = example["metadata"]["db_id"]
    schema_guidance = schema_guidance_by_db.get(db_id)

    if schema_guidance is None:
        raise KeyError(f"No schema guidance found for db_id: {db_id}")

    return "\n\n".join(
        [
            example["instruction"],
            SCHEMA_GROUNDING_RULES,
            "Schema guidance:",
            schema_guidance,
            example["input"],
        ]
    )


def convert_to_sft_example(example: dict, schema_guidance_by_db: dict[str, str]) -> dict:
    return {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            },
            {
                "role": "user",
                "content": build_user_message(example, schema_guidance_by_db),
            },
            {
                "role": "assistant",
                "content": example["output"],
            },
        ],
        "metadata": {
            **example["metadata"],
            "sft_format": "schema_guidance_v2",
        },
    }


def convert_file(input_path: Path, output_path: Path, schema_guidance_by_db: dict[str, str]) -> list[dict]:
    examples = read_jsonl(input_path)
    sft_examples = [
        convert_to_sft_example(example, schema_guidance_by_db)
        for example in examples
    ]
    write_jsonl(output_path, sft_examples)
    return sft_examples


def main() -> None:
    schema_guidance_by_db = read_json(SCHEMA_GUIDANCE_PATH)
    SFT_DIR.mkdir(parents=True, exist_ok=True)

    train_examples = convert_file(TRAIN_INPUT_PATH, TRAIN_OUTPUT_PATH, schema_guidance_by_db)
    validation_examples = convert_file(VALIDATION_INPUT_PATH, VALIDATION_OUTPUT_PATH, schema_guidance_by_db)

    print(f"Wrote train SFT V2 examples: {len(train_examples)} -> {TRAIN_OUTPUT_PATH}")
    print(f"Wrote validation SFT V2 examples: {len(validation_examples)} -> {VALIDATION_OUTPUT_PATH}")
    print("\nFirst train SFT V2 example:")
    print(json.dumps(train_examples[0], indent=2, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()

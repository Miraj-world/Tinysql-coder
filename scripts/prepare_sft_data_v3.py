"""Prepare join-focused SFT V3 data for LoRA Run 003.

Run 002 added schema guidance, but the model still struggled with joins and
table-column ownership. V3 keeps the SFT V2 prompt format and oversamples
training examples whose gold SQL uses joins.

This does not invent new labels. It changes the training distribution so the
model sees more examples of the behavior it is currently failing at.
"""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SFT_V2_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft_v2"
SFT_V3_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft_v3"

TRAIN_INPUT_PATH = SFT_V2_DIR / "train_sft_v2.jsonl"
VALIDATION_INPUT_PATH = SFT_V2_DIR / "validation_sft_v2.jsonl"
TRAIN_OUTPUT_PATH = SFT_V3_DIR / "train_sft_v3.jsonl"
VALIDATION_OUTPUT_PATH = SFT_V3_DIR / "validation_sft_v3.jsonl"

JOIN_PATTERN = re.compile(r"\bjoin\b", re.IGNORECASE)
JOIN_OVERSAMPLE_FACTOR = 2


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def assistant_sql(example: dict) -> str:
    return example["messages"][-1]["content"]


def is_join_example(example: dict) -> bool:
    return bool(JOIN_PATTERN.search(assistant_sql(example)))


def mark_format(example: dict, sft_format: str, is_join_focused_copy: bool) -> dict:
    return {
        **example,
        "metadata": {
            **example["metadata"],
            "sft_format": sft_format,
            "join_focused_copy": is_join_focused_copy,
        },
    }


def build_join_focused_train_set(examples: list[dict]) -> list[dict]:
    output_examples = []

    for example in examples:
        output_examples.append(mark_format(example, "schema_guidance_join_focus_v3", False))

        if is_join_example(example):
            for _ in range(JOIN_OVERSAMPLE_FACTOR - 1):
                output_examples.append(mark_format(example, "schema_guidance_join_focus_v3", True))

    return output_examples


def main() -> None:
    SFT_V3_DIR.mkdir(parents=True, exist_ok=True)

    train_examples = read_jsonl(TRAIN_INPUT_PATH)
    validation_examples = read_jsonl(VALIDATION_INPUT_PATH)

    join_train_examples = sum(is_join_example(example) for example in train_examples)
    join_validation_examples = sum(is_join_example(example) for example in validation_examples)

    train_v3_examples = build_join_focused_train_set(train_examples)
    validation_v3_examples = [
        mark_format(example, "schema_guidance_join_focus_v3", False)
        for example in validation_examples
    ]

    write_jsonl(TRAIN_OUTPUT_PATH, train_v3_examples)
    write_jsonl(VALIDATION_OUTPUT_PATH, validation_v3_examples)

    print(f"Original train examples: {len(train_examples)}")
    print(f"Join train examples: {join_train_examples}")
    print(f"V3 train examples after oversampling: {len(train_v3_examples)}")
    print(f"Validation examples: {len(validation_v3_examples)}")
    print(f"Join validation examples: {join_validation_examples}")
    print(f"Wrote train SFT V3: {TRAIN_OUTPUT_PATH}")
    print(f"Wrote validation SFT V3: {VALIDATION_OUTPUT_PATH}")


if __name__ == "__main__":
    main()

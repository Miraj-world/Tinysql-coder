"""Prepare hard-join-focused SFT V4 data for LoRA Run 004.

Run 003 improved execution accuracy by oversampling all join examples. The
successful join was simple, so V4 focuses more narrowly on harder join cases:
multi-table joins and subqueries.
"""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SFT_V2_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft_v2"
SFT_V4_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft_v4"

TRAIN_INPUT_PATH = SFT_V2_DIR / "train_sft_v2.jsonl"
VALIDATION_INPUT_PATH = SFT_V2_DIR / "validation_sft_v2.jsonl"
TRAIN_OUTPUT_PATH = SFT_V4_DIR / "train_sft_v4.jsonl"
VALIDATION_OUTPUT_PATH = SFT_V4_DIR / "validation_sft_v4.jsonl"

JOIN_PATTERN = re.compile(r"\bjoin\b", re.IGNORECASE)
SUBQUERY_PATTERN = re.compile(r"\(\s*select\b", re.IGNORECASE)

JOIN_OVERSAMPLE_FACTOR = 2
HARD_JOIN_OVERSAMPLE_FACTOR = 3


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def assistant_sql(example: dict) -> str:
    return example["messages"][-1]["content"]


def join_count(example: dict) -> int:
    return len(JOIN_PATTERN.findall(assistant_sql(example)))


def has_subquery(example: dict) -> bool:
    return bool(SUBQUERY_PATTERN.search(assistant_sql(example)))


def is_join_example(example: dict) -> bool:
    return join_count(example) > 0


def is_hard_join_example(example: dict) -> bool:
    return join_count(example) >= 2 or has_subquery(example)


def mark_format(example: dict, sft_format: str, copy_kind: str) -> dict:
    return {
        **example,
        "metadata": {
            **example["metadata"],
            "sft_format": sft_format,
            "oversample_copy_kind": copy_kind,
            "join_count": join_count(example),
            "has_subquery": has_subquery(example),
        },
    }


def copies_for_example(example: dict) -> int:
    if is_hard_join_example(example):
        return HARD_JOIN_OVERSAMPLE_FACTOR
    if is_join_example(example):
        return JOIN_OVERSAMPLE_FACTOR
    return 1


def copy_kind(example: dict, copy_index: int) -> str:
    if copy_index == 0:
        return "original"
    if is_hard_join_example(example):
        return "hard_join_extra"
    if is_join_example(example):
        return "join_extra"
    return "original"


def build_hard_join_train_set(examples: list[dict]) -> list[dict]:
    output_examples = []

    for example in examples:
        for copy_index in range(copies_for_example(example)):
            output_examples.append(
                mark_format(
                    example,
                    "schema_guidance_hard_join_focus_v4",
                    copy_kind(example, copy_index),
                )
            )

    return output_examples


def main() -> None:
    SFT_V4_DIR.mkdir(parents=True, exist_ok=True)

    train_examples = read_jsonl(TRAIN_INPUT_PATH)
    validation_examples = read_jsonl(VALIDATION_INPUT_PATH)

    train_v4_examples = build_hard_join_train_set(train_examples)
    validation_v4_examples = [
        mark_format(example, "schema_guidance_hard_join_focus_v4", "original")
        for example in validation_examples
    ]

    write_jsonl(TRAIN_OUTPUT_PATH, train_v4_examples)
    write_jsonl(VALIDATION_OUTPUT_PATH, validation_v4_examples)

    print(f"Original train examples: {len(train_examples)}")
    print(f"Join train examples: {sum(is_join_example(example) for example in train_examples)}")
    print(f"Hard join train examples: {sum(is_hard_join_example(example) for example in train_examples)}")
    print(f"V4 train examples after oversampling: {len(train_v4_examples)}")
    print(f"Validation examples: {len(validation_v4_examples)}")
    print(f"Join validation examples: {sum(is_join_example(example) for example in validation_examples)}")
    print(f"Hard join validation examples: {sum(is_hard_join_example(example) for example in validation_examples)}")
    print(f"Wrote train SFT V4: {TRAIN_OUTPUT_PATH}")
    print(f"Wrote validation SFT V4: {VALIDATION_OUTPUT_PATH}")


if __name__ == "__main__":
    main()

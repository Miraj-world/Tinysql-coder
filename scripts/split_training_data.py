"""Split processed examples into train and validation sets.

The split is stratified by difficulty so validation keeps a similar mix of
simple, moderate, and challenging examples.
"""

import json
import random
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed"
INPUT_PATH = PROCESSED_DIR / "training_data.jsonl"
TRAIN_PATH = PROCESSED_DIR / "train.jsonl"
VALIDATION_PATH = PROCESSED_DIR / "validation.jsonl"

VALIDATION_RATIO = 0.2
RANDOM_SEED = 42


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def difficulty_counts(examples: list[dict]) -> Counter:
    return Counter(
        example.get("metadata", {}).get("difficulty", "unknown")
        for example in examples
    )


def split_examples(examples: list[dict]) -> tuple[list[dict], list[dict]]:
    """Create a reproducible difficulty-balanced train/validation split."""
    random_generator = random.Random(RANDOM_SEED)
    grouped_examples = defaultdict(list)

    for example in examples:
        difficulty = example.get("metadata", {}).get("difficulty", "unknown")
        grouped_examples[difficulty].append(example)

    train_examples = []
    validation_examples = []

    for difficulty, group in grouped_examples.items():
        random_generator.shuffle(group)
        validation_count = round(len(group) * VALIDATION_RATIO)
        validation_examples.extend(group[:validation_count])
        train_examples.extend(group[validation_count:])

    random_generator.shuffle(train_examples)
    random_generator.shuffle(validation_examples)
    return train_examples, validation_examples


def print_split_summary(name: str, examples: list[dict]) -> None:
    print(f"{name}: {len(examples)} examples")
    for difficulty, count in sorted(difficulty_counts(examples).items()):
        print(f"  {difficulty}: {count}")


def main() -> None:
    examples = read_jsonl(INPUT_PATH)
    train_examples, validation_examples = split_examples(examples)

    write_jsonl(TRAIN_PATH, train_examples)
    write_jsonl(VALIDATION_PATH, validation_examples)

    print(f"Input: {INPUT_PATH}")
    print(f"Output train: {TRAIN_PATH}")
    print(f"Output validation: {VALIDATION_PATH}")
    print()
    print_split_summary("Train", train_examples)
    print()
    print_split_summary("Validation", validation_examples)


if __name__ == "__main__":
    main()

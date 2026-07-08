import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DATA_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed" / "training_data.jsonl"


def load_examples() -> list[dict]:
    with TRAINING_DATA_PATH.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def inspect_training_data() -> None:
    examples = load_examples()

    print(f"Training data path: {TRAINING_DATA_PATH}")
    print(f"Total examples: {len(examples)}")

    missing_instruction = sum(not example.get("instruction") for example in examples)
    missing_input = sum(not example.get("input") for example in examples)
    missing_output = sum(not example.get("output") for example in examples)
    print("\nMissing fields:")
    print(f"  instruction: {missing_instruction}")
    print(f"  input: {missing_input}")
    print(f"  output: {missing_output}")

    difficulty_counts = Counter(
        example.get("metadata", {}).get("difficulty", "unknown") for example in examples
    )
    print("\nDifficulty counts:")
    for difficulty, count in sorted(difficulty_counts.items()):
        print(f"  {difficulty}: {count}")

    print("\nFirst 5 readable examples:")
    for index, example in enumerate(examples[:5], start=1):
        metadata = example["metadata"]
        print("=" * 80)
        print(f"Example {index}")
        print(f"Question ID: {metadata['question_id']}")
        print(f"Database ID: {metadata['db_id']}")
        print(f"Difficulty: {metadata['difficulty']}")
        print("\nINPUT")
        print(example["input"])
        print("\nOUTPUT")
        print(example["output"])


if __name__ == "__main__":
    inspect_training_data()

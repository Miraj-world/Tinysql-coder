"""Freeze a leakage-checked unseen-question evaluation set from BIRD dev.

The project previously used all 500 BIRD mini-dev questions during model or
pipeline development. This script excludes those question IDs and texts, plus
exact question-text matches from the filtered training data, before sampling.
It does not inspect model predictions or SQL execution results while sampling.
"""

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

try:
    from scripts.create_baseline_eval_set import create_eval_record
except ModuleNotFoundError:
    # Support both ``python -m scripts...`` and direct script execution.
    from create_baseline_eval_set import create_eval_record


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEV_PATH = PROJECT_ROOT / "data" / "bird_unseen_dev" / "dev_20251106.jsonl"
MINI_DEV_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed" / "training_data.jsonl"
TRAIN_PATH = PROJECT_ROOT / "data" / "bird_train_filtered" / "train.jsonl"
SCHEMA_GUIDANCE_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema" / "schema_guidance.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "unseen-bird-dev-100" / "eval_set_100.jsonl"
AUDIT_PATH = PROJECT_ROOT / "outputs" / "unseen-bird-dev-100" / "sampling_audit.json"
SAMPLE_SIZE = 100
RANDOM_SEED = 20260715


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().casefold())


def mini_dev_question(record: dict) -> str:
    try:
        question_section = record["input"].split("\nQuestion: ", maxsplit=1)[1]
    except IndexError as error:
        raise ValueError("Mini-dev record has no Question section") from error
    return question_section.split("\nEvidence:", maxsplit=1)[0].strip()


def eligible_records(dev_records: list[dict], mini_records: list[dict], train_records: list[dict]) -> list[dict]:
    used_ids = {record["metadata"]["question_id"] for record in mini_records}
    used_questions = {normalize_question(mini_dev_question(record)) for record in mini_records}
    train_questions = {normalize_question(record["question"]) for record in train_records}
    return [
        record
        for record in dev_records
        if record["question_id"] not in used_ids
        and normalize_question(record["question"]) not in used_questions
        and normalize_question(record["question"]) not in train_questions
    ]


def proportional_allocations(records: list[dict], sample_size: int) -> dict[str, int]:
    """Allocate sample slots by difficulty using the largest-remainder method."""
    counts = Counter(record["difficulty"] for record in records)
    if sample_size > len(records):
        raise ValueError("Sample size exceeds the eligible record count")
    exact = {name: sample_size * count / len(records) for name, count in counts.items()}
    allocated = {name: int(value) for name, value in exact.items()}
    remaining = sample_size - sum(allocated.values())
    ranked = sorted(
        counts,
        key=lambda name: (-(exact[name] - allocated[name]), -counts[name], name),
    )
    for name in ranked[:remaining]:
        allocated[name] += 1
    return allocated


def choose_stratified_sample(records: list[dict], sample_size: int, seed: int) -> list[dict]:
    random_generator = random.Random(seed)
    allocations = proportional_allocations(records, sample_size)
    sample = []
    for difficulty in sorted(allocations):
        group = [record for record in records if record["difficulty"] == difficulty]
        random_generator.shuffle(group)
        sample.extend(group[: allocations[difficulty]])
    random_generator.shuffle(sample)
    return sample


def schema_from_guidance(guidance: str) -> str:
    ownership = guidance.split("Column ownership:\n", maxsplit=1)[-1]
    return ownership.split("\n\nPossible join keys:", maxsplit=1)[0].strip()


def to_processed_example(record: dict, schema_guidance: dict[str, str]) -> dict:
    db_id = record["db_id"]
    schema = schema_from_guidance(schema_guidance[db_id])
    sections = [f"Database ID: {db_id}", f"Schema:\n{schema}", f"Question: {record['question']}"]
    if record.get("evidence", "").strip():
        sections.append(f"Evidence: {record['evidence'].strip()}")
    return {
        "instruction": "Convert the database question into a valid SQL query.",
        "input": "\n".join(sections),
        "output": record["SQL"],
        "metadata": {
            "question_id": record["question_id"],
            "db_id": db_id,
            "difficulty": record["difficulty"],
        },
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-path", type=Path, default=DEV_PATH)
    parser.add_argument("--mini-dev-path", type=Path, default=MINI_DEV_PATH)
    parser.add_argument("--train-path", type=Path, default=TRAIN_PATH)
    parser.add_argument("--output-path", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--audit-path", type=Path, default=AUDIT_PATH)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dev_records = read_jsonl(args.dev_path)
    mini_records = read_jsonl(args.mini_dev_path)
    train_records = read_jsonl(args.train_path)
    schema_guidance = json.loads(SCHEMA_GUIDANCE_PATH.read_text(encoding="utf-8"))
    eligible = eligible_records(dev_records, mini_records, train_records)
    sample = choose_stratified_sample(eligible, args.sample_size, args.seed)
    eval_records = [
        create_eval_record(to_processed_example(record, schema_guidance), "direct_join_v9", schema_guidance)
        for record in sample
    ]
    write_jsonl(args.output_path, eval_records)

    audit = {
        "source": "birdsql/bird_sql_dev_20251106",
        "source_rows": len(dev_records),
        "excluded_mini_dev_ids": len({record["metadata"]["question_id"] for record in mini_records}),
        "eligible_rows": len(eligible),
        "sample_size": len(sample),
        "seed": args.seed,
        "prompt_style": "direct_join_v9",
        "difficulty_counts": dict(sorted(Counter(record["difficulty"] for record in sample).items())),
        "database_counts": dict(sorted(Counter(record["db_id"] for record in sample).items())),
        "question_ids": [record["question_id"] for record in sample],
        "known_schema_limitation": "Questions are unseen, but the 11 database schemas were used during development.",
    }
    args.audit_path.parent.mkdir(parents=True, exist_ok=True)
    args.audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    print(f"Wrote evaluation set: {args.output_path}")
    print(f"Wrote sampling audit: {args.audit_path}")


if __name__ == "__main__":
    main()

"""Prepare diverse BIRD-SQL SFT V8 data for LoRA Run 011.

V8 replaces repeated mini-dev examples with the official filtered BIRD train
split. Databases, rather than individual rows, are held out for validation so
the validation loss measures generalization to unseen schemas.
"""

import json
import random
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "data" / "bird_train_filtered"
OUTPUT_DIR = SOURCE_DIR / "sft_v8"

TRAIN_INPUT_PATH = SOURCE_DIR / "train.jsonl"
COLUMN_MEANING_PATH = SOURCE_DIR / "train_column_meaning.json"
MINI_DEV_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed" / "training_data.jsonl"
TRAIN_OUTPUT_PATH = OUTPUT_DIR / "train_sft_v8.jsonl"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "validation_sft_v8.jsonl"
SUMMARY_OUTPUT_PATH = OUTPUT_DIR / "preparation_summary.json"

RANDOM_SEED = 42
VALIDATION_RATIO = 0.10
SYSTEM_MESSAGE = "You are a careful text-to-SQL assistant. Return only SQL, with no markdown."
INSTRUCTION = "Convert the database question into a valid SQLite query."


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for row in rows:
            output_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def schemas_from_column_meanings(column_meanings: dict[str, str]) -> dict[str, str]:
    """Build compact ``table(column, ...)`` schemas from metadata keys."""
    schemas: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for key in column_meanings:
        parts = key.split("|", maxsplit=2)
        if len(parts) != 3:
            raise ValueError(f"Unexpected column-meaning key: {key!r}")
        db_id, table, column = parts
        schemas[db_id][table].append(column)

    return {
        db_id: "\n".join(
            f"{table}({', '.join(columns)})"
            for table, columns in sorted(tables.items())
        )
        for db_id, tables in schemas.items()
    }


def choose_validation_databases(
    rows: list[dict],
    validation_ratio: float = VALIDATION_RATIO,
    seed: int = RANDOM_SEED,
) -> set[str]:
    """Choose whole databases until validation is close to the target size."""
    rows_by_db: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        rows_by_db[row["db_id"]].append(row)

    db_ids = sorted(rows_by_db)
    random.Random(seed).shuffle(db_ids)
    target = round(len(rows) * validation_ratio)
    selected: set[str] = set()
    selected_rows = 0

    for db_id in db_ids:
        if selected_rows >= target:
            break
        selected.add(db_id)
        selected_rows += len(rows_by_db[db_id])

    return selected


def build_user_message(row: dict, schema: str) -> str:
    parts = [
        INSTRUCTION,
        f"Database ID: {row['db_id']}",
        f"Schema:\n{schema}",
        f"Question: {row['question'].strip()}",
    ]
    evidence = row.get("evidence", "").strip()
    if evidence:
        parts.append(f"Evidence: {evidence}")
    parts.append("Return only the SQL query.")
    return "\n\n".join(parts)


def convert_row(row: dict, schema: str, split: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": build_user_message(row, schema)},
            {"role": "assistant", "content": row["SQL"].strip()},
        ],
        "metadata": {
            "db_id": row["db_id"],
            "split": split,
            "sft_format": "bird_train_filtered_v8",
        },
    }


def mini_dev_questions(path: Path) -> set[str]:
    questions = set()
    for row in read_jsonl(path):
        question_section = row["input"].split("Question: ", maxsplit=1)[-1]
        question = question_section.split("\nEvidence:", maxsplit=1)[0]
        questions.add(question.strip().casefold())
    return questions


def prepare() -> dict:
    rows = read_jsonl(TRAIN_INPUT_PATH)
    column_meanings = json.loads(COLUMN_MEANING_PATH.read_text(encoding="utf-8"))
    schemas = schemas_from_column_meanings(column_meanings)

    missing_schemas = sorted({row["db_id"] for row in rows} - schemas.keys())
    if missing_schemas:
        raise ValueError(f"Missing schemas for databases: {missing_schemas}")

    leaked_questions = {
        row["question"].strip().casefold() for row in rows
    } & mini_dev_questions(MINI_DEV_PATH)
    if leaked_questions:
        raise ValueError(f"Found {len(leaked_questions)} exact mini-dev question overlaps")

    validation_db_ids = choose_validation_databases(rows)
    train_rows = [row for row in rows if row["db_id"] not in validation_db_ids]
    validation_rows = [row for row in rows if row["db_id"] in validation_db_ids]

    random_generator = random.Random(RANDOM_SEED)
    random_generator.shuffle(train_rows)
    random_generator.shuffle(validation_rows)

    train_sft = [convert_row(row, schemas[row["db_id"]], "train") for row in train_rows]
    validation_sft = [
        convert_row(row, schemas[row["db_id"]], "validation")
        for row in validation_rows
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(TRAIN_OUTPUT_PATH, train_sft)
    write_jsonl(VALIDATION_OUTPUT_PATH, validation_sft)

    train_db_ids = {row["db_id"] for row in train_rows}
    summary = {
        "source_rows": len(rows),
        "train_rows": len(train_sft),
        "validation_rows": len(validation_sft),
        "train_databases": len(train_db_ids),
        "validation_databases": len(validation_db_ids),
        "validation_database_ids": sorted(validation_db_ids),
        "database_overlap": sorted(train_db_ids & validation_db_ids),
        "exact_mini_dev_question_overlap": len(leaked_questions),
        "random_seed": RANDOM_SEED,
    }
    SUMMARY_OUTPUT_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    summary = prepare()
    print(json.dumps(summary, indent=2))
    print(f"Train SFT: {TRAIN_OUTPUT_PATH}")
    print(f"Validation SFT: {VALIDATION_OUTPUT_PATH}")


if __name__ == "__main__":
    main()

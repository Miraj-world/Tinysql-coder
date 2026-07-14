"""Prepare relationship-guided SFT V9 data for continued LoRA training."""

import json
import random
from pathlib import Path

try:
    from scripts.prepare_sft_data_v8 import (
        MINI_DEV_PATH,
        RANDOM_SEED,
        SOURCE_DIR,
        SYSTEM_MESSAGE,
        TRAIN_INPUT_PATH,
        choose_validation_databases,
        mini_dev_questions,
        read_jsonl,
        write_jsonl,
    )
except ModuleNotFoundError:
    from prepare_sft_data_v8 import (
        MINI_DEV_PATH,
        RANDOM_SEED,
        SOURCE_DIR,
        SYSTEM_MESSAGE,
        TRAIN_INPUT_PATH,
        choose_validation_databases,
        mini_dev_questions,
        read_jsonl,
        write_jsonl,
    )


OUTPUT_DIR = SOURCE_DIR / "sft_v9"
TABLE_SCHEMA_PATH = SOURCE_DIR / "train_tables.json"
TRAIN_OUTPUT_PATH = OUTPUT_DIR / "train_sft_v9.jsonl"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "validation_sft_v9.jsonl"
SUMMARY_OUTPUT_PATH = OUTPUT_DIR / "preparation_summary.json"


def guidance_from_table_schema(schema: dict) -> str:
    tables = schema["table_names_original"]
    columns = schema["column_names_original"]
    columns_by_table: list[list[str]] = [[] for _ in tables]
    for table_index, column in columns:
        if table_index >= 0:
            columns_by_table[table_index].append(column)

    ownership = [
        f"{table}: {', '.join(table_columns)}"
        for table, table_columns in zip(tables, columns_by_table)
    ]

    join_keys = []
    for left_index, right_index in schema["foreign_keys"]:
        left_table_index, left_column = columns[left_index]
        right_table_index, right_column = columns[right_index]
        join_keys.append(
            f"{tables[left_table_index]}.{left_column} = "
            f"{tables[right_table_index]}.{right_column}"
        )

    if not join_keys:
        join_keys = ["No declared foreign keys."]

    return "\n".join(
        [
            "Column ownership:",
            *ownership,
            "",
            "Possible join keys:",
            *sorted(join_keys, key=str.casefold),
        ]
    )


def join_guidance_from_table_schema(schema: dict, max_relationships: int = 12) -> str:
    """Return only foreign-key relationships to avoid duplicating the schema."""
    full_guidance = guidance_from_table_schema(schema)
    relationships = full_guidance.split("Possible join keys:\n", maxsplit=1)[1].splitlines()
    return "\n".join(relationships[:max_relationships])


def compact_schema(schema: dict) -> str:
    tables = schema["table_names_original"]
    columns_by_table: list[list[str]] = [[] for _ in tables]
    for table_index, column in schema["column_names_original"]:
        if table_index >= 0:
            columns_by_table[table_index].append(column)
    return "\n".join(
        f"{table}({', '.join(columns)})"
        for table, columns in zip(tables, columns_by_table)
    )


def build_user_message(row: dict, schema: dict) -> str:
    parts = [
        "Convert the database question into a valid SQLite query.",
        "Possible join keys:",
        join_guidance_from_table_schema(schema),
        f"Database ID: {row['db_id']}",
        f"Schema:\n{compact_schema(schema)}",
        f"Question: {row['question'].strip()}",
    ]
    evidence = row.get("evidence", "").strip()
    if evidence:
        parts.append(f"Evidence: {evidence}")
    parts.append("Return only the SQL query.")
    return "\n\n".join(parts)


def convert_row(row: dict, schema: dict, split: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": build_user_message(row, schema)},
            {"role": "assistant", "content": row["SQL"].strip()},
        ],
        "metadata": {
            "db_id": row["db_id"],
            "split": split,
            "sft_format": "bird_train_relationship_guided_v9",
        },
    }


def prepare() -> dict:
    rows = read_jsonl(TRAIN_INPUT_PATH)
    schemas = {
        schema["db_id"]: schema
        for schema in json.loads(TABLE_SCHEMA_PATH.read_text(encoding="utf-8"))
    }
    row_db_ids = {row["db_id"] for row in rows}
    if row_db_ids != set(schemas):
        raise ValueError("Training row and table schema database IDs do not match")

    leaked_questions = {
        row["question"].strip().casefold() for row in rows
    } & mini_dev_questions(MINI_DEV_PATH)
    if leaked_questions:
        raise ValueError(f"Found {len(leaked_questions)} exact mini-dev question overlaps")

    validation_db_ids = choose_validation_databases(rows)
    train_rows = [row for row in rows if row["db_id"] not in validation_db_ids]
    validation_rows = [row for row in rows if row["db_id"] in validation_db_ids]
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(train_rows)
    rng.shuffle(validation_rows)

    train_sft = [convert_row(row, schemas[row["db_id"]], "train") for row in train_rows]
    validation_sft = [
        convert_row(row, schemas[row["db_id"]], "validation") for row in validation_rows
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
        "database_overlap": sorted(train_db_ids & validation_db_ids),
        "exact_mini_dev_question_overlap": len(leaked_questions),
        "schema_source": "Deema/BIRD-SQL train_tables.json mirror, pinned revision",
        "random_seed": RANDOM_SEED,
    }
    SUMMARY_OUTPUT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    print(json.dumps(prepare(), indent=2))
    print(f"Train SFT: {TRAIN_OUTPUT_PATH}")
    print(f"Validation SFT: {VALIDATION_OUTPUT_PATH}")


if __name__ == "__main__":
    main()

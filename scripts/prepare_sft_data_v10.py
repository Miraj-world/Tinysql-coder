"""Prepare value-context-aligned BIRD training data for Qwen 3B Run 014."""

import json
import re
from pathlib import Path

try:
    from scripts.augment_eval_with_values import STOP_WORDS, contains_word_sequence, normalized_words
    from scripts.prepare_sft_data_v8 import (
        COLUMN_MEANING_PATH,
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
    from scripts.prepare_sft_data_v9 import (
        build_user_message,
        compact_schema,
        join_guidance_from_table_schema,
    )
except ModuleNotFoundError:
    from augment_eval_with_values import STOP_WORDS, contains_word_sequence, normalized_words
    from prepare_sft_data_v8 import (
        COLUMN_MEANING_PATH,
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
    from prepare_sft_data_v9 import build_user_message, compact_schema, join_guidance_from_table_schema


OUTPUT_DIR = SOURCE_DIR / "sft_v10"
TABLE_SCHEMA_PATH = SOURCE_DIR / "train_tables.json"
TRAIN_OUTPUT_PATH = OUTPUT_DIR / "train_sft_v10.jsonl"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "validation_sft_v10.jsonl"
SUMMARY_OUTPUT_PATH = OUTPUT_DIR / "preparation_summary.json"
MAX_HINTS = 8


def meaningful_words(text: str) -> list[str]:
    return [word for word in normalized_words(text) if word not in STOP_WORDS]


def column_hint_score(table: str, column: str, description: str, query: str) -> float:
    query_words = meaningful_words(query)
    query_set = set(query_words)
    column_words = meaningful_words(column)
    table_words = meaningful_words(table)
    description_words = set(meaningful_words(description))
    score = 0.0
    if contains_word_sequence(query_words, column_words):
        score += 100.0
    score += 12.0 * len(set(column_words) & query_set)
    score += 3.0 * len(set(table_words) & query_set)
    score += min(2.0 * len(description_words & query_set), 20.0)
    return score


def relevant_column_hints(row: dict, column_meanings: dict[str, str]) -> list[str]:
    query = f"{row['question']} {row.get('evidence', '')}".strip()
    prefix = f"{row['db_id']}|"
    scored: list[tuple[float, str]] = []
    for key, description in column_meanings.items():
        if not key.startswith(prefix):
            continue
        _, table, column = key.split("|", maxsplit=2)
        score = column_hint_score(table, column, description, query)
        if score <= 0:
            continue
        compact_description = re.sub(r"\s+", " ", description).strip()[:320]
        scored.append((score, f"{table}.{column}: {compact_description}"))
    scored.sort(key=lambda item: (-item[0], item[1].casefold()))
    return [hint for _, hint in scored[:MAX_HINTS]]


def value_aligned_user_message(row: dict, schema: dict, column_meanings: dict[str, str]) -> str:
    original = build_user_message(row, schema)
    hints = relevant_column_hints(row, column_meanings)
    if not hints:
        return original
    marker = "\n\nReturn only the SQL query."
    section = "\n\nRelevant database values:\n" + "\n".join(hints)
    return original.replace(marker, section + marker, 1)


def convert_row(row: dict, schema: dict, column_meanings: dict[str, str], split: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": value_aligned_user_message(row, schema, column_meanings)},
            {"role": "assistant", "content": row["SQL"].strip()},
        ],
        "metadata": {
            "db_id": row["db_id"],
            "split": split,
            "sft_format": "bird_train_value_context_v10",
        },
    }


def prepare() -> dict:
    rows = read_jsonl(TRAIN_INPUT_PATH)
    column_meanings = json.loads(COLUMN_MEANING_PATH.read_text(encoding="utf-8"))
    schemas = {
        schema["db_id"]: schema
        for schema in json.loads(TABLE_SCHEMA_PATH.read_text(encoding="utf-8"))
    }
    leaked_questions = {
        row["question"].strip().casefold() for row in rows
    } & mini_dev_questions(MINI_DEV_PATH)
    if leaked_questions:
        raise ValueError(f"Found {len(leaked_questions)} exact mini-dev question overlaps")

    validation_db_ids = choose_validation_databases(rows)
    train_rows = [row for row in rows if row["db_id"] not in validation_db_ids]
    validation_rows = [row for row in rows if row["db_id"] in validation_db_ids]

    train_sft = [convert_row(row, schemas[row["db_id"]], column_meanings, "train") for row in train_rows]
    validation_sft = [
        convert_row(row, schemas[row["db_id"]], column_meanings, "validation")
        for row in validation_rows
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(TRAIN_OUTPUT_PATH, train_sft)
    write_jsonl(VALIDATION_OUTPUT_PATH, validation_sft)

    summary = {
        "source_rows": len(rows),
        "train_rows": len(train_sft),
        "validation_rows": len(validation_sft),
        "train_databases": len({row["db_id"] for row in train_rows}),
        "validation_databases": len(validation_db_ids),
        "database_overlap": sorted(
            {row["db_id"] for row in train_rows} & validation_db_ids
        ),
        "exact_mini_dev_question_overlap": len(leaked_questions),
        "max_relevant_column_hints": MAX_HINTS,
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

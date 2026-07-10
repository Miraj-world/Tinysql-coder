"""Prepare error-aware SFT V6 data for LoRA Run 006.

V5 taught a verbose ownership plan before SQL and hurt execution accuracy.
V6 keeps the idea, but makes it shorter and more decision-focused: choose the
query plan type, name the key source tables, then put executable SQL after
``FINAL_SQL:``.
"""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed"
SCHEMA_GUIDANCE_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema" / "schema_guidance.json"
SFT_V6_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft_v6"

TRAIN_INPUT_PATH = PROCESSED_DIR / "train.jsonl"
VALIDATION_INPUT_PATH = PROCESSED_DIR / "validation.jsonl"
TRAIN_OUTPUT_PATH = SFT_V6_DIR / "train_sft_v6.jsonl"
VALIDATION_OUTPUT_PATH = SFT_V6_DIR / "validation_sft_v6.jsonl"

SYSTEM_MESSAGE = (
    "You are a careful text-to-SQL assistant. Use only the provided schema. "
    "Choose a short plan type, then put executable SQL after FINAL_SQL:."
)

ERROR_AWARE_RULES = """Before writing SQL:
1. Choose PLAN_TYPE: local_schema_fix, lookup_or_value_fix, fact_table_first, or fresh_query_plan.
2. Use local_schema_fix only for simple column/table ownership issues.
3. Use fact_table_first when the question is really about events, matches, transactions, results, or other fact rows.
4. Use fresh_query_plan when the question needs a subquery, date transform, UNION, CTE, or multi-step aggregation.
5. End with FINAL_SQL: followed by only the SQL query."""

JOIN_PATTERN = re.compile(r"\bjoin\b", re.IGNORECASE)
SUBQUERY_PATTERN = re.compile(r"\(\s*select\b", re.IGNORECASE)
CTE_PATTERN = re.compile(r"^\s*with\b", re.IGNORECASE)
UNION_PATTERN = re.compile(r"\bunion\b", re.IGNORECASE)
DATE_FUNCTION_PATTERN = re.compile(r"\b(?:strftime|substr|substring)\s*\(", re.IGNORECASE)
AGGREGATE_PATTERN = re.compile(r"\b(?:count|sum|avg|min|max)\s*\(", re.IGNORECASE)
GROUP_PATTERN = re.compile(r"\bgroup\s+by\b", re.IGNORECASE)
ORDER_LIMIT_PATTERN = re.compile(r"\border\s+by\b.*\blimit\b", re.IGNORECASE | re.DOTALL)
CASE_PATTERN = re.compile(r"\b(?:case|iif)\b", re.IGNORECASE)
STRING_COMPARISON_PATTERN = re.compile(r"\b[A-Za-z_][\w]*\.[A-Za-z_][\w]*\s*=\s*'", re.IGNORECASE)
TABLE_PATTERN = re.compile(
    r"\b(?:from|join)\s+[`\"]?(?P<table>[A-Za-z_][\w]*)[`\"]?",
    re.IGNORECASE,
)

FACT_TABLE_HINTS = {
    "match",
    "matches",
    "transactions",
    "transactions_1k",
    "results",
    "races",
    "laptimes",
    "pitstops",
    "comments",
    "posts",
    "expense",
    "income",
    "attendance",
    "yearmonth",
    "atom",
    "molecule",
}

FRESH_PLAN_OVERSAMPLE_FACTOR = 3
FACT_TABLE_OVERSAMPLE_FACTOR = 2


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def join_count(sql: str) -> int:
    return len(JOIN_PATTERN.findall(sql))


def has_subquery(sql: str) -> bool:
    return bool(SUBQUERY_PATTERN.search(sql))


def has_fresh_plan_shape(sql: str) -> bool:
    return any(
        [
            has_subquery(sql),
            bool(CTE_PATTERN.search(sql)),
            bool(UNION_PATTERN.search(sql)),
            bool(DATE_FUNCTION_PATTERN.search(sql)),
            bool(GROUP_PATTERN.search(sql)) and bool(ORDER_LIMIT_PATTERN.search(sql)),
        ]
    )


def tables_used(sql: str) -> list[str]:
    seen = set()
    tables = []
    for match in TABLE_PATTERN.finditer(sql):
        table = match.group("table")
        key = table.lower()
        if key not in seen:
            seen.add(key)
            tables.append(table)
    return tables


def fact_tables_used(sql: str) -> list[str]:
    return [
        table
        for table in tables_used(sql)
        if table.lower() in FACT_TABLE_HINTS
    ]


def plan_type_for_sql(sql: str) -> str:
    if has_fresh_plan_shape(sql):
        return "fresh_query_plan"
    if fact_tables_used(sql):
        return "fact_table_first"
    if STRING_COMPARISON_PATTERN.search(sql):
        return "lookup_or_value_fix"
    return "local_schema_fix"


def special_operations(sql: str) -> list[str]:
    operations = []
    if has_subquery(sql):
        operations.append("subquery")
    if CTE_PATTERN.search(sql):
        operations.append("cte")
    if UNION_PATTERN.search(sql):
        operations.append("union")
    if DATE_FUNCTION_PATTERN.search(sql):
        operations.append("date_or_text_transform")
    if AGGREGATE_PATTERN.search(sql):
        operations.append("aggregation")
    if GROUP_PATTERN.search(sql):
        operations.append("grouping")
    if ORDER_LIMIT_PATTERN.search(sql):
        operations.append("ranking_or_extreme_value")
    if not operations:
        operations.append("direct_select")
    return operations


def build_user_message(example: dict, schema_guidance_by_db: dict[str, str]) -> str:
    db_id = example["metadata"]["db_id"]
    schema_guidance = schema_guidance_by_db.get(db_id)
    if schema_guidance is None:
        raise KeyError(f"No schema guidance found for db_id: {db_id}")

    return "\n\n".join(
        [
            example["instruction"],
            ERROR_AWARE_RULES,
            "Schema guidance:",
            schema_guidance,
            example["input"],
        ]
    )


def build_assistant_message(sql: str) -> str:
    used_tables = tables_used(sql)
    facts = fact_tables_used(sql)
    if not used_tables:
        used_tables = ["choose from schema"]
    if not facts:
        facts = ["not required"]

    return "\n".join(
        [
            f"PLAN_TYPE: {plan_type_for_sql(sql)}",
            f"SOURCE_TABLES: {', '.join(used_tables[:6])}",
            f"FACT_TABLES: {', '.join(facts[:4])}",
            f"SPECIAL_OPERATIONS: {', '.join(special_operations(sql))}",
            "FINAL_SQL:",
            sql,
        ]
    )


def convert_to_sft_example(
    example: dict,
    schema_guidance_by_db: dict[str, str],
    copy_kind: str,
) -> dict:
    sql = example["output"]
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
                "content": build_assistant_message(sql),
            },
        ],
        "metadata": {
            **example["metadata"],
            "sft_format": "error_aware_v6",
            "plan_type": plan_type_for_sql(sql),
            "copy_kind": copy_kind,
            "join_count": join_count(sql),
            "has_subquery": has_subquery(sql),
            "has_fresh_plan_shape": has_fresh_plan_shape(sql),
        },
    }


def copies_for_sql(sql: str) -> int:
    if has_fresh_plan_shape(sql):
        return FRESH_PLAN_OVERSAMPLE_FACTOR
    if fact_tables_used(sql):
        return FACT_TABLE_OVERSAMPLE_FACTOR
    return 1


def copy_kind_for_sql(sql: str, copy_index: int) -> str:
    if copy_index == 0:
        return "original"
    if has_fresh_plan_shape(sql):
        return "fresh_plan_extra"
    if fact_tables_used(sql):
        return "fact_table_extra"
    return "original"


def convert_train_file(
    input_path: Path,
    output_path: Path,
    schema_guidance_by_db: dict[str, str],
) -> list[dict]:
    examples = read_jsonl(input_path)
    sft_examples = []

    for example in examples:
        sql = example["output"]
        for copy_index in range(copies_for_sql(sql)):
            sft_examples.append(
                convert_to_sft_example(
                    example,
                    schema_guidance_by_db,
                    copy_kind_for_sql(sql, copy_index),
                )
            )

    write_jsonl(output_path, sft_examples)
    return sft_examples


def convert_validation_file(
    input_path: Path,
    output_path: Path,
    schema_guidance_by_db: dict[str, str],
) -> list[dict]:
    examples = read_jsonl(input_path)
    sft_examples = [
        convert_to_sft_example(example, schema_guidance_by_db, "original")
        for example in examples
    ]
    write_jsonl(output_path, sft_examples)
    return sft_examples


def count_by_plan_type(examples: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for example in examples:
        plan_type = example["metadata"]["plan_type"]
        counts[plan_type] = counts.get(plan_type, 0) + 1
    return dict(sorted(counts.items()))


def main() -> None:
    schema_guidance_by_db = read_json(SCHEMA_GUIDANCE_PATH)
    SFT_V6_DIR.mkdir(parents=True, exist_ok=True)

    train_examples = convert_train_file(TRAIN_INPUT_PATH, TRAIN_OUTPUT_PATH, schema_guidance_by_db)
    validation_examples = convert_validation_file(
        VALIDATION_INPUT_PATH,
        VALIDATION_OUTPUT_PATH,
        schema_guidance_by_db,
    )

    print(f"Wrote train SFT V6 examples: {len(train_examples)} -> {TRAIN_OUTPUT_PATH}")
    print(f"Wrote validation SFT V6 examples: {len(validation_examples)} -> {VALIDATION_OUTPUT_PATH}")
    print(f"Train plan types: {count_by_plan_type(train_examples)}")
    print(f"Validation plan types: {count_by_plan_type(validation_examples)}")
    print(f"Train fresh-plan examples: {sum(example['metadata']['has_fresh_plan_shape'] for example in train_examples)}")
    print(f"Train fact-table examples: {sum(bool(example['metadata']['plan_type'] == 'fact_table_first') for example in train_examples)}")
    print("\nFirst train SFT V6 example:")
    print(json.dumps(train_examples[0], indent=2, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()

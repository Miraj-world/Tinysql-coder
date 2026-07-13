"""Prepare source-table-supervised SFT V7 data for LoRA Run 008.

V7 keeps the compact V6 plan format, but adds gold-query-derived table labels:
the source tables used by the gold SQL and the primary fact table. The goal is
to teach the model which tables to choose before it writes joins and filters.
"""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed"
SCHEMA_GUIDANCE_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema" / "schema_guidance.json"
SFT_V7_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft_v7"

TRAIN_INPUT_PATH = PROCESSED_DIR / "train.jsonl"
VALIDATION_INPUT_PATH = PROCESSED_DIR / "validation.jsonl"
TRAIN_OUTPUT_PATH = SFT_V7_DIR / "train_sft_v7.jsonl"
VALIDATION_OUTPUT_PATH = SFT_V7_DIR / "validation_sft_v7.jsonl"

SYSTEM_MESSAGE = (
    "You are a careful text-to-SQL assistant. Use only the provided schema. "
    "Choose source tables before writing SQL, then put executable SQL after FINAL_SQL:."
)

SOURCE_TABLE_RULES = """Before writing SQL:
1. Choose PLAN_TYPE: local_schema_fix, lookup_or_value_fix, fact_table_first, or fresh_query_plan.
2. List REQUIRED_SOURCE_TABLES before writing joins.
3. Choose PRIMARY_FACT_TABLE: the table that contains the main rows being counted, averaged, filtered, or ranked.
4. Do not join through a table just because it has a similar column name.
5. End with FINAL_SQL: followed by only the SQL query."""

JOIN_PATTERN = re.compile(r"\bjoin\b", re.IGNORECASE)
SUBQUERY_PATTERN = re.compile(r"\(\s*select\b", re.IGNORECASE)
CTE_PATTERN = re.compile(r"^\s*with\b", re.IGNORECASE)
UNION_PATTERN = re.compile(r"\bunion\b", re.IGNORECASE)
DATE_FUNCTION_PATTERN = re.compile(r"\b(?:strftime|substr|substring)\s*\(", re.IGNORECASE)
AGGREGATE_PATTERN = re.compile(r"\b(?:count|sum|avg|min|max)\s*\(", re.IGNORECASE)
GROUP_PATTERN = re.compile(r"\bgroup\s+by\b", re.IGNORECASE)
ORDER_LIMIT_PATTERN = re.compile(r"\border\s+by\b.*\blimit\b", re.IGNORECASE | re.DOTALL)
STRING_COMPARISON_PATTERN = re.compile(r"\b[A-Za-z_][\w]*\.[A-Za-z_][\w]*\s*=\s*'", re.IGNORECASE)
TABLE_PATTERN = re.compile(
    r"\b(?:from|join)\s+[`\"]?(?P<table>[A-Za-z_][\w]*)[`\"]?",
    re.IGNORECASE,
)

FACT_TABLE_HINTS = {
    "atom",
    "attendance",
    "budget",
    "comments",
    "expense",
    "income",
    "laptimes",
    "match",
    "molecule",
    "pitstops",
    "posts",
    "races",
    "results",
    "transactions",
    "transactions_1k",
    "yearmonth",
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


def parse_schema_tables(schema_guidance: str) -> list[str]:
    tables = []
    in_ownership = False

    for raw_line in schema_guidance.splitlines():
        line = raw_line.strip()
        if line == "Column ownership:":
            in_ownership = True
            continue
        if line == "Possible join keys:":
            break
        if in_ownership and ": " in line:
            table, _ = line.split(": ", maxsplit=1)
            tables.append(table)

    return tables


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


def tables_used(sql: str, schema_tables: list[str]) -> list[str]:
    table_by_lower = {table.lower(): table for table in schema_tables}
    seen = set()
    tables = []

    for match in TABLE_PATTERN.finditer(sql):
        table = match.group("table")
        schema_table = table_by_lower.get(table.lower())
        if schema_table is None:
            continue
        key = schema_table.lower()
        if key not in seen:
            seen.add(key)
            tables.append(schema_table)

    return tables


def fact_tables_used(source_tables: list[str]) -> list[str]:
    return [
        table
        for table in source_tables
        if table.lower() in FACT_TABLE_HINTS
    ]


def primary_fact_table(source_tables: list[str]) -> str:
    facts = fact_tables_used(source_tables)
    if facts:
        return facts[0]
    if source_tables:
        return source_tables[0]
    return "not required"


def plan_type_for_sql(sql: str, source_tables: list[str]) -> str:
    if has_fresh_plan_shape(sql):
        return "fresh_query_plan"
    if fact_tables_used(source_tables):
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
            SOURCE_TABLE_RULES,
            "Schema guidance:",
            schema_guidance,
            example["input"],
        ]
    )


def build_assistant_message(sql: str, schema_guidance: str) -> str:
    schema_tables = parse_schema_tables(schema_guidance)
    source_tables = tables_used(sql, schema_tables)
    if not source_tables:
        source_tables = ["choose from schema"]

    return "\n".join(
        [
            f"PLAN_TYPE: {plan_type_for_sql(sql, source_tables)}",
            f"REQUIRED_SOURCE_TABLES: {', '.join(source_tables[:8])}",
            f"PRIMARY_FACT_TABLE: {primary_fact_table(source_tables)}",
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
    db_id = example["metadata"]["db_id"]
    schema_guidance = schema_guidance_by_db[db_id]
    source_tables = tables_used(sql, parse_schema_tables(schema_guidance))
    plan_type = plan_type_for_sql(sql, source_tables)

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
                "content": build_assistant_message(sql, schema_guidance),
            },
        ],
        "metadata": {
            **example["metadata"],
            "sft_format": "source_table_supervised_v7",
            "plan_type": plan_type,
            "copy_kind": copy_kind,
            "join_count": join_count(sql),
            "has_subquery": has_subquery(sql),
            "has_fresh_plan_shape": has_fresh_plan_shape(sql),
            "source_tables": source_tables,
            "primary_fact_table": primary_fact_table(source_tables),
        },
    }


def copies_for_sql(sql: str, source_tables: list[str]) -> int:
    if has_fresh_plan_shape(sql):
        return FRESH_PLAN_OVERSAMPLE_FACTOR
    if fact_tables_used(source_tables):
        return FACT_TABLE_OVERSAMPLE_FACTOR
    return 1


def copy_kind_for_sql(sql: str, source_tables: list[str], copy_index: int) -> str:
    if copy_index == 0:
        return "original"
    if has_fresh_plan_shape(sql):
        return "fresh_plan_extra"
    if fact_tables_used(source_tables):
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
        schema_guidance = schema_guidance_by_db[example["metadata"]["db_id"]]
        source_tables = tables_used(sql, parse_schema_tables(schema_guidance))
        for copy_index in range(copies_for_sql(sql, source_tables)):
            sft_examples.append(
                convert_to_sft_example(
                    example,
                    schema_guidance_by_db,
                    copy_kind_for_sql(sql, source_tables, copy_index),
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


def count_metadata(examples: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for example in examples:
        value = str(example["metadata"][key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def main() -> None:
    schema_guidance_by_db = read_json(SCHEMA_GUIDANCE_PATH)
    SFT_V7_DIR.mkdir(parents=True, exist_ok=True)

    train_examples = convert_train_file(TRAIN_INPUT_PATH, TRAIN_OUTPUT_PATH, schema_guidance_by_db)
    validation_examples = convert_validation_file(
        VALIDATION_INPUT_PATH,
        VALIDATION_OUTPUT_PATH,
        schema_guidance_by_db,
    )

    print(f"Wrote train SFT V7 examples: {len(train_examples)} -> {TRAIN_OUTPUT_PATH}")
    print(f"Wrote validation SFT V7 examples: {len(validation_examples)} -> {VALIDATION_OUTPUT_PATH}")
    print(f"Train plan types: {count_metadata(train_examples, 'plan_type')}")
    print(f"Validation plan types: {count_metadata(validation_examples, 'plan_type')}")
    print(f"Train primary fact tables: {count_metadata(train_examples, 'primary_fact_table')}")
    print("\nFirst train SFT V7 example:")
    print(json.dumps(train_examples[0], indent=2, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()

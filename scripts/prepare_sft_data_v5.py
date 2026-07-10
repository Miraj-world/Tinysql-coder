"""Prepare ownership-teacher SFT V5 data for LoRA Run 005.

Run 004 improved the score, but failure analysis still showed mostly
wrong-table-for-column mistakes. V5 changes the assistant target: before the
final SQL, the model learns a compact plan that names column ownership and join
keys. The final query is still marked with ``FINAL_SQL:`` so evaluation can
extract only executable SQL.
"""

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "processed"
SCHEMA_GUIDANCE_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema" / "schema_guidance.json"
SFT_V5_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft_v5"

TRAIN_INPUT_PATH = PROCESSED_DIR / "train.jsonl"
VALIDATION_INPUT_PATH = PROCESSED_DIR / "validation.jsonl"
TRAIN_OUTPUT_PATH = SFT_V5_DIR / "train_sft_v5.jsonl"
VALIDATION_OUTPUT_PATH = SFT_V5_DIR / "validation_sft_v5.jsonl"

SYSTEM_MESSAGE = (
    "You are a careful text-to-SQL assistant. Use only the provided schema. "
    "Think through column ownership, then put the executable query after FINAL_SQL:."
)

SCHEMA_GROUNDING_RULES = """Before writing SQL:
1. Identify each important column and the table that owns it.
2. Identify the join keys needed to connect those tables.
3. Do not place a column on a table unless that column is listed under that table.
4. End with FINAL_SQL: followed by only the SQL query."""

JOIN_PATTERN = re.compile(r"\bjoin\b", re.IGNORECASE)
SUBQUERY_PATTERN = re.compile(r"\(\s*select\b", re.IGNORECASE)
TABLE_PATTERN = re.compile(
    r"\b(?:from|join)\s+([A-Za-z_][\w]*)\s*(?:as\s+)?([A-Za-z_][\w]*)?",
    re.IGNORECASE,
)
QUALIFIED_COLUMN_PATTERN = re.compile(r"\b([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\b")
BARE_IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][\w]*\b")
SQL_KEYWORDS = {
    "as",
    "asc",
    "avg",
    "between",
    "by",
    "case",
    "cast",
    "count",
    "desc",
    "distinct",
    "else",
    "end",
    "float",
    "from",
    "group",
    "having",
    "iif",
    "in",
    "inner",
    "is",
    "join",
    "limit",
    "max",
    "min",
    "not",
    "null",
    "on",
    "or",
    "order",
    "real",
    "select",
    "strftime",
    "substr",
    "substring",
    "sum",
    "then",
    "union",
    "where",
    "with",
}


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_schema_guidance(schema_guidance: str) -> tuple[dict[str, list[str]], list[str]]:
    ownership: dict[str, list[str]] = {}
    join_keys: list[str] = []
    section = None

    for raw_line in schema_guidance.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "Column ownership:":
            section = "ownership"
            continue
        if line == "Possible join keys:":
            section = "join_keys"
            continue

        if section == "ownership":
            table, columns = line.split(": ", maxsplit=1)
            ownership[table] = [column.strip() for column in columns.split(",")]
        elif section == "join_keys":
            join_keys.append(line)

    return ownership, join_keys


def build_alias_map(sql: str) -> dict[str, str]:
    aliases = {}
    for table, alias in TABLE_PATTERN.findall(sql):
        aliases[table] = table
        if alias and alias.lower() not in {"where", "on", "inner", "join", "group", "order", "limit"}:
            aliases[alias] = table
    return aliases


def table_for_column(column: str, ownership: dict[str, list[str]]) -> str | None:
    column_lower = column.lower()
    owners = [
        table
        for table, columns in ownership.items()
        if any(candidate.lower() == column_lower for candidate in columns)
    ]
    if len(owners) == 1:
        return owners[0]
    if owners:
        return "/".join(owners)
    return None


def used_column_ownership(sql: str, ownership: dict[str, list[str]]) -> list[str]:
    alias_map = build_alias_map(sql)
    notes = []
    seen = set()

    for alias, column in QUALIFIED_COLUMN_PATTERN.findall(sql):
        table = alias_map.get(alias, alias)
        key = (column.lower(), table.lower())
        if key not in seen:
            seen.add(key)
            notes.append(f"{column} -> {table}")

    for identifier in BARE_IDENTIFIER_PATTERN.findall(sql):
        identifier_lower = identifier.lower()
        if identifier_lower in SQL_KEYWORDS or identifier in alias_map:
            continue
        owner = table_for_column(identifier, ownership)
        if owner is None:
            continue
        key = (identifier_lower, owner.lower())
        if key not in seen:
            seen.add(key)
            notes.append(f"{identifier} -> {owner}")

    return notes[:12]


def used_join_keys(sql: str, join_keys: list[str]) -> list[str]:
    compact_sql = re.sub(r"\s+", "", sql).lower()
    used = []

    for join_key in join_keys:
        left, right = [part.strip() for part in join_key.split("=", maxsplit=1)]
        left_column = left.split(".")[-1]
        right_column = right.split(".")[-1]
        if left_column.lower() in compact_sql and right_column.lower() in compact_sql:
            used.append(join_key)

    return used[:8]


def join_count(sql: str) -> int:
    return len(JOIN_PATTERN.findall(sql))


def has_subquery(sql: str) -> bool:
    return bool(SUBQUERY_PATTERN.search(sql))


def build_user_message(example: dict, schema_guidance_by_db: dict[str, str]) -> str:
    db_id = example["metadata"]["db_id"]
    schema_guidance = schema_guidance_by_db.get(db_id)
    if schema_guidance is None:
        raise KeyError(f"No schema guidance found for db_id: {db_id}")

    return "\n\n".join(
        [
            example["instruction"],
            SCHEMA_GROUNDING_RULES,
            "Schema guidance:",
            schema_guidance,
            example["input"],
        ]
    )


def build_assistant_message(example: dict, schema_guidance: str) -> str:
    sql = example["output"]
    ownership, join_keys = parse_schema_guidance(schema_guidance)
    ownership_notes = used_column_ownership(sql, ownership)
    join_key_notes = used_join_keys(sql, join_keys)

    if not ownership_notes:
        ownership_notes = ["Use only columns listed in the schema."]
    if not join_key_notes:
        join_key_notes = ["No join key needed."]

    return "\n".join(
        [
            "COLUMN_OWNERSHIP:",
            *[f"- {note}" for note in ownership_notes],
            "JOIN_PATH:",
            *[f"- {note}" for note in join_key_notes],
            "FINAL_SQL:",
            sql,
        ]
    )


def convert_to_sft_example(example: dict, schema_guidance_by_db: dict[str, str]) -> dict:
    db_id = example["metadata"]["db_id"]
    schema_guidance = schema_guidance_by_db[db_id]
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
                "content": build_assistant_message(example, schema_guidance),
            },
        ],
        "metadata": {
            **example["metadata"],
            "sft_format": "ownership_teacher_v5",
            "join_count": join_count(sql),
            "has_subquery": has_subquery(sql),
        },
    }


def convert_file(input_path: Path, output_path: Path, schema_guidance_by_db: dict[str, str]) -> list[dict]:
    examples = read_jsonl(input_path)
    sft_examples = [
        convert_to_sft_example(example, schema_guidance_by_db)
        for example in examples
    ]
    write_jsonl(output_path, sft_examples)
    return sft_examples


def main() -> None:
    schema_guidance_by_db = read_json(SCHEMA_GUIDANCE_PATH)
    SFT_V5_DIR.mkdir(parents=True, exist_ok=True)

    train_examples = convert_file(TRAIN_INPUT_PATH, TRAIN_OUTPUT_PATH, schema_guidance_by_db)
    validation_examples = convert_file(VALIDATION_INPUT_PATH, VALIDATION_OUTPUT_PATH, schema_guidance_by_db)

    print(f"Wrote train SFT V5 examples: {len(train_examples)} -> {TRAIN_OUTPUT_PATH}")
    print(f"Wrote validation SFT V5 examples: {len(validation_examples)} -> {VALIDATION_OUTPUT_PATH}")
    print(f"Train join examples: {sum(example['metadata']['join_count'] > 0 for example in train_examples)}")
    print(f"Train subquery examples: {sum(example['metadata']['has_subquery'] for example in train_examples)}")
    print("\nFirst train SFT V5 example:")
    print(json.dumps(train_examples[0], indent=2, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()

"""Inspect the most useful hard failures from an evaluation run.

Failure counts are helpful, but the next training idea usually comes from a few
concrete examples. This script extracts hard failures and adds a small mentor
diagnosis for what the model needed to know.
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASES_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "dev_databases"
DEFAULT_EVAL_PATH = PROJECT_ROOT / "outputs" / "lora-run-004" / "execution_eval.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "analysis" / "lora-run-004-hard-failures.md"

NO_SUCH_COLUMN_RE = re.compile(r"no such column: (?P<name>.+)", re.IGNORECASE)
TABLE_ALIAS_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+[`\"]?(?P<table>[A-Za-z_][\w]*)[`\"]?"
    r"(?:\s+(?:AS\s+)?(?P<alias>[A-Za-z_][\w]*))?",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect hard SQL failures from an evaluation run.")
    parser.add_argument("--eval-path", type=Path, default=DEFAULT_EVAL_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--max-examples", type=int, default=8)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def sqlite_path_for_database(db_id: str) -> Path:
    return DATABASES_DIR / db_id / f"{db_id}.sqlite"


def load_schema(db_id: str) -> dict[str, set[str]]:
    schema = {}
    with sqlite3.connect(sqlite_path_for_database(db_id)) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for (table_name,) in tables:
            columns = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
            schema[table_name.lower()] = {column[1].lower() for column in columns}
    return schema


def column_owners(schema: dict[str, set[str]]) -> dict[str, list[str]]:
    owners = {}
    for table_name, columns in schema.items():
        for column in columns:
            owners.setdefault(column, []).append(table_name)
    return owners


def parse_aliases(sql: str) -> dict[str, str]:
    aliases = {}
    for match in TABLE_ALIAS_RE.finditer(sql):
        table = match.group("table")
        alias = match.group("alias") or table
        if alias.upper() in {"WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "ON", "GROUP", "ORDER"}:
            alias = table
        aliases[alias.lower()] = table.lower()
    return aliases


def split_column_reference(reference: str) -> tuple[str | None, str]:
    cleaned = reference.strip().strip("`\"[]")
    if "." not in cleaned:
        return None, cleaned.lower()
    alias, column = cleaned.split(".", 1)
    return alias.strip("`\"[]").lower(), column.strip("`\"[]").lower()


def diagnose(record: dict, schema_cache: dict[str, dict[str, set[str]]]) -> str:
    error = record["predicted_error"] or ""
    match = NO_SUCH_COLUMN_RE.search(error)
    if not match:
        if record["predicted_ok"]:
            return "The SQL executed, but the logic returned different rows than the gold SQL."
        return f"Execution error: {error}"

    schema = schema_cache.setdefault(record["db_id"], load_schema(record["db_id"]))
    owners = column_owners(schema)
    aliases = parse_aliases(record["predicted_sql"])
    alias, column = split_column_reference(match.group("name"))
    actual_owners = owners.get(column, [])

    if alias and alias in aliases and actual_owners:
        predicted_table = aliases[alias]
        return (
            f"The model put column `{column}` on `{predicted_table}`, "
            f"but that column belongs to {', '.join(f'`{owner}`' for owner in actual_owners)}."
        )

    if actual_owners:
        return f"The model used `{column}` without grounding it to {', '.join(f'`{owner}`' for owner in actual_owners)}."

    return f"The model invented column `{column}`; it does not exist in `{record['db_id']}`."


def sql_block(sql: str) -> str:
    return f"```sql\n{sql.strip()}\n```"


def is_hard_failure(record: dict) -> bool:
    if record["execution_match"]:
        return False
    if record["difficulty"] in {"moderate", "challenging"}:
        return True
    return bool(record["predicted_error"])


def build_report(records: list[dict], max_examples: int) -> str:
    schema_cache: dict[str, dict[str, set[str]]] = {}
    failures = [record for record in records if is_hard_failure(record)]

    lines = [
        "# Hard Failure Inspection",
        "",
        f"Hard failures selected: {min(len(failures), max_examples)}/{len(failures)}",
        "",
        "## Mentor Pattern",
        "",
        "The next training format should teach this sequence explicitly:",
        "",
        "```text",
        "needed columns -> owning tables -> join path -> final SQL",
        "```",
        "",
        "## Examples",
        "",
    ]

    for record in failures[:max_examples]:
        lines.extend(
            [
                f"### Question {record['question_id']}",
                "",
                f"- Database: `{record['db_id']}`",
                f"- Difficulty: `{record['difficulty']}`",
                f"- Diagnosis: {diagnose(record, schema_cache)}",
                "",
                "**Predicted SQL**",
                "",
                sql_block(record["predicted_sql"]),
                "",
                "**Gold SQL**",
                "",
                sql_block(record["expected_sql"]),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    records = read_jsonl(args.eval_path)
    report = build_report(records, args.max_examples)

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(report, encoding="utf-8")

    print(f"Loaded examples: {len(records)}")
    print(f"Wrote hard failure report: {args.output_path}")


if __name__ == "__main__":
    main()

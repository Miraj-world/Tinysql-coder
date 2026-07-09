"""Analyze SQL evaluation failures against the real database schemas.

Scores tell us whether a run worked. Failure patterns tell us what to fix next.
This script reads an execution-evaluation JSONL file and classifies common
text-to-SQL mistakes such as hallucinated tables or columns attached to the
wrong table alias.
"""

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_PATH = PROJECT_ROOT / "outputs" / "lora-run-001" / "execution_eval.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "analysis" / "lora-run-001-failure-analysis.md"
DATABASES_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "dev_databases"

NO_SUCH_COLUMN_RE = re.compile(r"no such column: (?P<name>.+)", re.IGNORECASE)
NO_SUCH_TABLE_RE = re.compile(r"no such table: (?P<name>.+)", re.IGNORECASE)
TABLE_ALIAS_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+[`\"]?(?P<table>[A-Za-z_][\w]*)[`\"]?"
    r"(?:\s+(?:AS\s+)?(?P<alias>[A-Za-z_][\w]*))?",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze SQL execution failure patterns.")
    parser.add_argument("--eval-path", type=Path, default=DEFAULT_EVAL_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def sqlite_path_for_database(db_id: str) -> Path:
    sqlite_path = DATABASES_DIR / db_id / f"{db_id}.sqlite"
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    return sqlite_path


def load_schema(db_id: str) -> dict[str, set[str]]:
    """Return table -> lowercase columns for one SQLite database."""
    sqlite_path = sqlite_path_for_database(db_id)
    schema: dict[str, set[str]] = {}

    with sqlite3.connect(sqlite_path) as connection:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()

        for (table_name,) in table_rows:
            columns = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
            schema[table_name.lower()] = {column[1].lower() for column in columns}

    return schema


def build_column_owners(schema: dict[str, set[str]]) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = defaultdict(list)
    for table_name, columns in schema.items():
        for column_name in columns:
            owners[column_name].append(table_name)
    return dict(owners)


def parse_aliases(sql: str) -> dict[str, str]:
    """Return alias -> table from FROM/JOIN clauses.

    The parser is intentionally small. It is good enough for diagnosis, not for
    rewriting SQL.
    """
    aliases: dict[str, str] = {}

    for match in TABLE_ALIAS_RE.finditer(sql):
        table = match.group("table")
        alias = match.group("alias") or table

        # Avoid treating SQL keywords as aliases when the table has no alias.
        if alias.upper() in {"WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "ON", "GROUP", "ORDER"}:
            alias = table

        aliases[alias.lower()] = table.lower()

    return aliases


def split_column_reference(column_reference: str) -> tuple[str | None, str]:
    cleaned = column_reference.strip().strip("`\"[]")

    if "." not in cleaned:
        return None, cleaned.lower()

    alias, column = cleaned.split(".", 1)
    return alias.strip("`\"[]").lower(), column.strip("`\"[]").lower()


def classify_no_such_column(record: dict, schema: dict[str, set[str]]) -> tuple[str, str]:
    error = record["predicted_error"] or ""
    match = NO_SUCH_COLUMN_RE.search(error)
    if not match:
        return "execution_error_other", error

    alias, column = split_column_reference(match.group("name"))
    aliases = parse_aliases(record["predicted_sql"])
    owners = build_column_owners(schema)
    actual_owners = owners.get(column, [])

    if alias and alias in aliases:
        predicted_table = aliases[alias]
        if actual_owners:
            detail = (
                f"column `{column}` was referenced on `{predicted_table}`, "
                f"but exists on {', '.join(f'`{owner}`' for owner in actual_owners)}"
            )
            return "wrong_table_for_column", detail

        return "invented_column", f"column `{column}` does not exist in `{record['db_id']}`"

    if actual_owners:
        detail = f"unqualified column `{column}` exists on {', '.join(f'`{owner}`' for owner in actual_owners)}"
        return "ambiguous_or_unqualified_column", detail

    return "invented_column", f"column `{column}` does not exist in `{record['db_id']}`"


def classify_record(record: dict, schema_cache: dict[str, dict[str, set[str]]]) -> tuple[str, str]:
    if record["execution_match"]:
        return "execution_match", "prediction returned the same rows as gold SQL"

    if record["predicted_ok"]:
        return "executes_wrong_result", "prediction executed but returned different rows"

    error = record["predicted_error"] or ""
    db_id = record["db_id"]
    schema = schema_cache.setdefault(db_id, load_schema(db_id))

    table_match = NO_SUCH_TABLE_RE.search(error)
    if table_match:
        table_name = table_match.group("name").strip().strip("`\"[]")
        return "hallucinated_table", f"table `{table_name}` does not exist in `{db_id}`"

    if NO_SUCH_COLUMN_RE.search(error):
        return classify_no_such_column(record, schema)

    return "execution_error_other", error


def sql_block(sql: str) -> str:
    return f"```sql\n{sql.strip()}\n```"


def build_report(records: list[dict], classifications: list[dict]) -> str:
    counts = Counter(item["category"] for item in classifications)
    total = len(records)

    lines = [
        "# Failure Pattern Analysis",
        "",
        "## Summary",
        "",
        f"Total evaluated examples: {total}",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]

    for category, count in counts.most_common():
        lines.append(f"| `{category}` | {count} |")

    lines.extend(
        [
            "",
            "## What This Means",
            "",
            "The dominant failure categories should guide the next training change.",
            "",
            "- `wrong_table_for_column`: the model knows a real column name, but attaches it to the wrong table.",
            "- `invented_column`: the model creates a column that does not exist in the database.",
            "- `hallucinated_table`: the model creates a table that does not exist in the database.",
            "- `executes_wrong_result`: the SQL runs, but returns different rows from the gold SQL.",
            "",
            "## Examples",
            "",
        ]
    )

    for item in classifications:
        if item["category"] == "execution_match":
            continue

        record = item["record"]
        lines.extend(
            [
                f"### Question {record['question_id']}",
                "",
                f"- Database: `{record['db_id']}`",
                f"- Difficulty: `{record['difficulty']}`",
                f"- Category: `{item['category']}`",
                f"- Detail: {item['detail']}",
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
    schema_cache: dict[str, dict[str, set[str]]] = {}

    classifications = []
    for record in records:
        category, detail = classify_record(record, schema_cache)
        classifications.append(
            {
                "record": record,
                "category": category,
                "detail": detail,
            }
        )

    report = build_report(records, classifications)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(report, encoding="utf-8")

    counts = Counter(item["category"] for item in classifications)
    print(f"Analyzed examples: {len(records)}")
    for category, count in counts.most_common():
        print(f"{category}: {count}")
    print(f"Wrote failure analysis: {args.output_path}")


if __name__ == "__main__":
    main()

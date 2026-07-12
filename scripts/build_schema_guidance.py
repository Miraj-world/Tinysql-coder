"""Build schema guidance for stronger text-to-SQL fine-tuning.

The compact schema text shows tables and columns, but Eval 005 showed that the
model still puts columns on the wrong tables. This script creates a more
explicit guide:

1. Column ownership: which columns belong to each table.
2. Join hints: real SQLite foreign keys plus conservative identifier-like
   shared columns.

The output is still text, because we want it to fit naturally inside the SFT
user prompt for LoRA Run 002.
"""

import json
import sqlite3
from itertools import combinations
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASES_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "dev_databases"
OUTPUT_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema"
OUTPUT_PATH = OUTPUT_DIR / "schema_guidance.json"


def quote_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def find_sqlite_file(database_dir: Path) -> Path:
    sqlite_files = sorted(database_dir.glob("*.sqlite"))
    if not sqlite_files:
        raise FileNotFoundError(f"No .sqlite file found in {database_dir}")
    if len(sqlite_files) > 1:
        raise ValueError(f"Expected one .sqlite file in {database_dir}, found {len(sqlite_files)}")
    return sqlite_files[0]


def get_table_names(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def get_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [row[1] for row in rows]


def load_database_schema(sqlite_path: Path) -> dict[str, list[str]]:
    with sqlite3.connect(sqlite_path) as connection:
        return {
            table_name: get_columns(connection, table_name)
            for table_name in get_table_names(connection)
        }


def get_primary_keys(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [row[1] for row in rows if row[5]]


def foreign_key_join_hints(connection: sqlite3.Connection, schema: dict[str, list[str]]) -> list[str]:
    """Return joins declared in SQLite metadata.

    Some BIRD SQLite files name the target table but omit the target column.
    When the target table has exactly one primary key, we infer that primary key.
    """
    table_by_lower = {
        table_name.lower(): table_name
        for table_name in schema
    }
    primary_keys = {
        table_name.lower(): get_primary_keys(connection, table_name)
        for table_name in schema
    }
    hints = []

    for table_name in schema:
        rows = connection.execute(f"PRAGMA foreign_key_list({quote_identifier(table_name)})").fetchall()
        for row in rows:
            target_table = row[2]
            source_column = row[3]
            target_column = row[4]
            if target_table is None or source_column is None:
                continue
            target_table = table_by_lower.get(target_table.lower(), target_table)
            if target_column is None and len(primary_keys.get(target_table.lower(), [])) == 1:
                target_column = primary_keys[target_table.lower()][0]
            if target_column is None:
                continue
            hints.append(f"{table_name}.{source_column} = {target_table}.{target_column}")

    return sorted(set(hints), key=str.lower)


def is_safe_inferred_join_column(column: str) -> bool:
    """Return whether a shared column name is specific enough for a join hint."""
    column_lower = column.lower()
    generic_columns = {
        "id",
        "name",
        "date",
        "time",
        "type",
        "status",
        "url",
        "position",
        "points",
        "rank",
        "year",
    }
    if column_lower in generic_columns:
        return False
    return any(
        token in column_lower
        for token in ["id", "uuid", "code", "ref"]
    )


def inferred_join_hints(schema: dict[str, list[str]], existing_hints: list[str]) -> list[str]:
    """Infer simple join hints from safe exact shared identifier columns.

    This is a heuristic, not a perfect relationship extractor. It is useful for
    BIRD-style prompts because some useful joins are not declared as SQLite
    foreign keys. Keep it narrow so the prompt does not teach false joins like
    `Country.id = Player.id` or `circuits.url = drivers.url`.
    """
    existing = {join_hint_key(hint) for hint in existing_hints}
    hints = []

    for left_table, right_table in combinations(schema, 2):
        left_columns = {column.lower(): column for column in schema[left_table]}
        right_columns = {column.lower(): column for column in schema[right_table]}
        shared_column_keys = sorted(set(left_columns) & set(right_columns))

        for column_key in shared_column_keys:
            left_column = left_columns[column_key]
            right_column = right_columns[column_key]
            if not is_safe_inferred_join_column(left_column):
                continue
            hint = f"{left_table}.{left_column} = {right_table}.{right_column}"
            if join_hint_key(hint) not in existing:
                hints.append(hint)

    return sorted(set(hints), key=str.lower)


def join_hint_key(hint: str) -> tuple[str, str]:
    left, right = [part.strip().lower() for part in hint.split("=", maxsplit=1)]
    return tuple(sorted([left, right]))


def likely_join_hints(connection: sqlite3.Connection, schema: dict[str, list[str]]) -> list[str]:
    foreign_key_hints = foreign_key_join_hints(connection, schema)
    inferred_hints = inferred_join_hints(schema, foreign_key_hints)
    deduped_hints = []
    seen = set()

    for hint in foreign_key_hints + inferred_hints:
        key = join_hint_key(hint)
        if key in seen:
            continue
        seen.add(key)
        deduped_hints.append(hint)

    return deduped_hints


def format_schema_guidance(connection: sqlite3.Connection, schema: dict[str, list[str]]) -> str:
    column_lines = [
        f"{table_name}: {', '.join(columns)}"
        for table_name, columns in schema.items()
    ]
    join_hints = likely_join_hints(connection, schema)

    sections = [
        "Column ownership:",
        *column_lines,
    ]

    if join_hints:
        sections.extend(
            [
                "",
                "Possible join keys:",
                *join_hints,
            ]
        )
    else:
        sections.extend(
            [
                "",
                "Possible join keys:",
                "No exact shared column names found.",
            ]
        )

    return "\n".join(sections)


def build_all_guidance() -> dict[str, str]:
    guidance_by_database = {}

    for database_dir in sorted(DATABASES_DIR.iterdir()):
        if not database_dir.is_dir():
            continue

        sqlite_path = find_sqlite_file(database_dir)
        with sqlite3.connect(sqlite_path) as connection:
            schema = load_database_schema(sqlite_path)
            guidance_by_database[database_dir.name] = format_schema_guidance(connection, schema)

    return guidance_by_database


def main() -> None:
    guidance_by_database = build_all_guidance()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(guidance_by_database, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Built schema guidance for databases: {len(guidance_by_database)}")
    print(f"Wrote schema guidance to: {OUTPUT_PATH}")

    first_database = sorted(guidance_by_database)[0]
    print()
    print(f"Example guidance for {first_database}:")
    print(guidance_by_database[first_database][:2000])


if __name__ == "__main__":
    main()

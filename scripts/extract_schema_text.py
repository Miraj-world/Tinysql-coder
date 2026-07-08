import json
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASES_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "dev_databases"
OUTPUT_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "schema"
OUTPUT_PATH = OUTPUT_DIR / "schema_text.json"


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


def get_column_names(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [row[1] for row in rows]


def quote_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def compact_table_schema(table_name: str, column_names: list[str]) -> str:
    columns = ", ".join(column_names)
    return f"{table_name}({columns})"


def extract_schema_text(sqlite_path: Path) -> str:
    with sqlite3.connect(sqlite_path) as connection:
        table_schemas = []
        for table_name in get_table_names(connection):
            column_names = get_column_names(connection, table_name)
            table_schemas.append(compact_table_schema(table_name, column_names))

    return "\n".join(table_schemas)


def extract_all_schema_text() -> dict[str, str]:
    schema_by_database = {}

    for database_dir in sorted(DATABASES_DIR.iterdir()):
        if not database_dir.is_dir():
            continue

        sqlite_path = find_sqlite_file(database_dir)
        schema_by_database[database_dir.name] = extract_schema_text(sqlite_path)

    return schema_by_database


def main() -> None:
    schema_by_database = extract_all_schema_text()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(schema_by_database, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Extracted schemas: {len(schema_by_database)}")
    print(f"Wrote schema text to: {OUTPUT_PATH}")

    first_database = sorted(schema_by_database)[0]
    print()
    print(f"Example schema for {first_database}:")
    print(schema_by_database[first_database])


if __name__ == "__main__":
    main()

"""Repair simple schema-grounding errors in generated SQL predictions.

This is a post-generation experiment. It makes conservative layered repairs:

1. Alias repair: the correct owning table is already present in the SQL.
2. Join repair: the correct owning table is missing, but a direct foreign-key
   join from an existing table is available.
3. Lookup repair: an ID foreign-key column is compared to a human-readable
   string value that belongs in a lookup table.
4. Value repair: a string literal has the wrong casing for a real database
   value.
5. Foreign-key PK inference: a table-level foreign key omits the target column,
   but the target table has one clear primary-key column.
6. Join pruning: a leading joined table is not referenced outside the join
   condition.
7. Distinct repair: a simple single-column projection returns duplicate rows.
8. Unqualified-column repair: a flat joined query uses a bare column name and
   exactly one table already in the query owns it.
9. Undeclared-alias repair: a flat query uses an alias that was never declared,
   and exactly one table already in the query owns the referenced column.
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = PROJECT_ROOT / "outputs" / "lora-run-004" / "predictions.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "lora-run-004-table-repaired" / "predictions.jsonl"
DATABASES_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "dev_databases"

NO_SUCH_COLUMN_RE = re.compile(r"no such column: (?P<name>.+)", re.IGNORECASE)
QUALIFIED_COLUMN_RE = re.compile(
    r"\b(?P<alias>[A-Za-z_][\w]*)\."
    r"(?P<quote>[`\"]?)(?P<column>[A-Za-z_][\w]*)(?P=quote)"
    r"(?=\W|$)"
)
STRING_COMPARISON_RE = re.compile(
    r"\b(?P<alias>[A-Za-z_][\w]*)\.(?P<column>[A-Za-z_][\w]*)\s*=\s*'(?P<value>(?:''|[^'])*)'",
    re.IGNORECASE,
)
LEADING_INNER_JOIN_RE = re.compile(
    r"(?P<prefix>\bFROM\s+)"
    r"[`\"]?(?P<left_table>[A-Za-z_][\w]*)[`\"]?"
    r"(?:\s+(?:AS\s+)?(?P<left_alias>[A-Za-z_][\w]*))?"
    r"\s+INNER\s+JOIN\s+"
    r"[`\"]?(?P<right_table>[A-Za-z_][\w]*)[`\"]?"
    r"(?:\s+(?:AS\s+)?(?P<right_alias>[A-Za-z_][\w]*))?"
    r"\s+ON\s+(?P<on_clause>.*?)(?=\b(?:INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\b|$)",
    re.IGNORECASE,
)
SIMPLE_SELECT_COLUMN_RE = re.compile(
    r"^\s*SELECT\s+(?!DISTINCT\b)(?P<column>[A-Za-z_][\w]*\.[A-Za-z_][\w]*)\s+FROM\b",
    re.IGNORECASE,
)
SELECT_RE = re.compile(r"\bSELECT\b", re.IGNORECASE)
TABLE_ALIAS_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+[`\"]?(?P<table>[A-Za-z_][\w]*)[`\"]?"
    r"(?:\s+(?:AS\s+)?(?P<alias>[A-Za-z_][\w]*))?",
    re.IGNORECASE,
)
SQL_KEYWORD_ALIASES = {"WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "ON", "GROUP", "ORDER", "LIMIT"}
CLAUSE_START_RE = re.compile(r"\b(?:WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair conservative SQL alias/column ownership errors.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--max-passes", type=int, default=5)
    parser.add_argument(
        "--disable-join-repair",
        action="store_true",
        help="Only repair wrong aliases for tables already present in the SQL.",
    )
    parser.add_argument(
        "--disable-semantic-repair",
        action="store_true",
        help="Do not run post-execution repairs such as lookup, value, pruning, or DISTINCT repair.",
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def sqlite_path_for_database(db_id: str) -> Path:
    sqlite_path = DATABASES_DIR / db_id / f"{db_id}.sqlite"
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    return sqlite_path


def load_database_info(db_id: str) -> dict:
    schema: dict[str, set[str]] = {}
    column_types: dict[str, dict[str, str]] = {}
    primary_keys: dict[str, list[str]] = {}
    foreign_keys: list[tuple[str, str, str, str]] = []
    with sqlite3.connect(sqlite_path_for_database(db_id)) as connection:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()

        for (table_name,) in table_rows:
            columns = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
            table_key = table_name.lower()
            schema[table_key] = {column[1].lower() for column in columns}
            column_types[table_key] = {
                column[1].lower(): (column[2] or "").lower()
                for column in columns
            }
            primary_keys[table_key] = [
                column[1].lower()
                for column in columns
                if column[5]
            ]

        for (table_name,) in table_rows:
            for foreign_key in connection.execute(f'PRAGMA foreign_key_list("{table_name}")').fetchall():
                if foreign_key[2] is None or foreign_key[3] is None:
                    continue
                target_table = foreign_key[2].lower()
                target_column = foreign_key[4].lower() if foreign_key[4] is not None else None
                if target_column is None and len(primary_keys.get(target_table, [])) == 1:
                    target_column = primary_keys[target_table][0]
                if target_column is None:
                    continue
                foreign_keys.append(
                    (
                        table_name.lower(),
                        foreign_key[3].lower(),
                        target_table,
                        target_column,
                    )
                )

    return {
        "schema": schema,
        "column_types": column_types,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys,
    }


def normalize_value(value: object) -> object:
    if isinstance(value, float):
        return round(value, 6)
    return value


def normalize_rows(rows: list[tuple]) -> list[list[object]]:
    normalized_rows = [[normalize_value(value) for value in row] for row in rows]
    return sorted(normalized_rows, key=lambda row: json.dumps(row, sort_keys=True, default=str))


def execute_sql(db_id: str, sql: str) -> dict:
    try:
        with sqlite3.connect(sqlite_path_for_database(db_id)) as connection:
            rows = connection.execute(sql).fetchall()
        return {"ok": True, "rows": normalize_rows(rows), "error": None}
    except Exception as error:
        return {"ok": False, "rows": None, "error": str(error)}


def parse_aliases(sql: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for match in TABLE_ALIAS_RE.finditer(sql):
        table = match.group("table")
        alias = match.group("alias") or table
        if alias.upper() in SQL_KEYWORD_ALIASES:
            alias = table
        aliases[alias.lower()] = table.lower()
    return aliases


def split_column_reference(column_reference: str) -> tuple[str | None, str]:
    cleaned = column_reference.strip().strip("`\"[]")
    if "." not in cleaned:
        return None, cleaned.lower()
    alias, column = cleaned.split(".", maxsplit=1)
    return alias.strip("`\"[]").lower(), column.strip("`\"[]").lower()


def build_owner_aliases(schema: dict[str, set[str]], aliases: dict[str, str]) -> dict[str, list[str]]:
    owner_aliases: dict[str, list[str]] = {}
    for alias, table in aliases.items():
        for column in schema.get(table, set()):
            owner_aliases.setdefault(column, []).append(alias)
    return owner_aliases


def owner_tables_for_column(schema: dict[str, set[str]], column: str) -> list[str]:
    return [table for table, columns in schema.items() if column in columns]


def next_table_alias(aliases: dict[str, str]) -> str:
    index = 1
    while f"t{index}" in aliases:
        index += 1
    return f"T{index}"


def has_nested_select(sql: str) -> bool:
    matches = list(SELECT_RE.finditer(sql))
    return len(matches) > 1


def find_direct_join(
    existing_aliases: dict[str, str],
    missing_table: str,
    foreign_keys: list[tuple[str, str, str, str]],
) -> tuple[str, str, str, str] | None:
    candidates: list[tuple[str, str, str, str]] = []

    for from_table, from_column, to_table, to_column in foreign_keys:
        for existing_alias, existing_table in existing_aliases.items():
            if from_table == missing_table and to_table == existing_table:
                candidates.append((existing_alias, to_column, from_column, missing_table))
            elif from_table == existing_table and to_table == missing_table:
                candidates.append((existing_alias, from_column, to_column, missing_table))

    unique_candidates = sorted(set(candidates))
    if len(unique_candidates) != 1:
        return None
    return unique_candidates[0]


def find_foreign_key_target(
    source_table: str,
    source_column: str,
    foreign_keys: list[tuple[str, str, str, str]],
) -> tuple[str, str] | None:
    candidates = [
        (target_table, target_column)
        for from_table, from_column, target_table, target_column in foreign_keys
        if from_table == source_table and from_column == source_column
    ]
    unique_candidates = sorted(set(candidates))
    if len(unique_candidates) != 1:
        return None
    return unique_candidates[0]


def text_columns_for_table(database_info: dict, table: str) -> list[str]:
    columns = database_info["schema"].get(table, set())
    column_types = database_info["column_types"].get(table, {})
    text_columns = []

    for column in columns:
        declared_type = column_types.get(column, "")
        looks_like_text = any(type_name in declared_type for type_name in ["char", "clob", "text", "varchar"])
        looks_like_label = column not in {"url"} and not column.endswith("_id") and column != "id"
        if looks_like_text and looks_like_label:
            text_columns.append(column)

    return sorted(text_columns)


def matching_label_columns(db_id: str, table: str, value: str, database_info: dict) -> list[str]:
    matches = []

    with sqlite3.connect(sqlite_path_for_database(db_id)) as connection:
        for column in text_columns_for_table(database_info, table):
            query = f'SELECT 1 FROM "{table}" WHERE LOWER("{column}") = LOWER(?) LIMIT 1'
            if connection.execute(query, (value,)).fetchone():
                matches.append(column)

    return matches


def canonical_value_for_column(db_id: str, table: str, column: str, value: str) -> str | None:
    query = f'SELECT DISTINCT "{column}" FROM "{table}" WHERE LOWER("{column}") = LOWER(?) LIMIT 2'

    with sqlite3.connect(sqlite_path_for_database(db_id)) as connection:
        rows = connection.execute(query, (value,)).fetchall()

    values = [row[0] for row in rows if isinstance(row[0], str)]
    if len(values) != 1 or values[0] == value:
        return None
    return values[0]


def replace_string_literal_for_column(
    sql: str,
    target_alias: str,
    target_column: str,
    old_value: str,
    new_value: str,
) -> str:
    replaced = False

    def replace_match(match: re.Match) -> str:
        nonlocal replaced
        if replaced:
            return match.group(0)
        if (
            match.group("alias").lower() == target_alias
            and match.group("column").lower() == target_column
            and match.group("value").replace("''", "'") == old_value
        ):
            replaced = True
            escaped_value = new_value.replace("'", "''")
            return f"{match.group('alias')}.{match.group('column')} = '{escaped_value}'"
        return match.group(0)

    return STRING_COMPARISON_RE.sub(replace_match, sql)


def alias_reference_pattern(alias: str) -> re.Pattern:
    return re.compile(rf"\b{re.escape(alias)}\.", re.IGNORECASE)


def is_simple_two_alias_join(on_clause: str, left_alias: str, right_alias: str) -> bool:
    simple_join_re = re.compile(
        rf"^\s*(?:{re.escape(left_alias)}\.[A-Za-z_][\w]*\s*=\s*{re.escape(right_alias)}\.[A-Za-z_][\w]*|"
        rf"{re.escape(right_alias)}\.[A-Za-z_][\w]*\s*=\s*{re.escape(left_alias)}\.[A-Za-z_][\w]*)\s*$",
        re.IGNORECASE,
    )
    return bool(simple_join_re.match(on_clause))


def leading_join_prune_for_sql(sql: str) -> tuple[str, str] | None:
    if has_nested_select(sql):
        return None

    match = LEADING_INNER_JOIN_RE.search(sql)
    if match is None:
        return None

    left_table = match.group("left_table")
    right_table = match.group("right_table")
    left_alias = match.group("left_alias") or left_table
    right_alias = match.group("right_alias") or right_table

    if left_alias.upper() in SQL_KEYWORD_ALIASES or right_alias.upper() in SQL_KEYWORD_ALIASES:
        return None

    if not is_simple_two_alias_join(match.group("on_clause"), left_alias, right_alias):
        return None

    before_join = sql[: match.start()]
    after_join = sql[match.end() :]
    if alias_reference_pattern(left_alias).search(before_join + after_join):
        return None

    right_from = f"FROM {right_table} AS {right_alias}"
    repaired_sql = f"{before_join}{right_from} {after_join.lstrip()}".rstrip()
    note = f"removed leading unused join table {left_table} AS {left_alias}"
    return repaired_sql, note


def has_duplicate_rows(rows: list[list[object]]) -> bool:
    seen = set()
    for row in rows:
        row_key = json.dumps(row, sort_keys=True, default=str)
        if row_key in seen:
            return True
        seen.add(row_key)
    return False


def distinct_repair_for_sql(db_id: str, sql: str) -> tuple[str, str] | None:
    if has_nested_select(sql):
        return None
    if re.search(r"\b(?:COUNT|SUM|AVG|MIN|MAX)\s*\(", sql, re.IGNORECASE):
        return None
    if re.search(r"\bGROUP\s+BY\b", sql, re.IGNORECASE):
        return None

    match = SIMPLE_SELECT_COLUMN_RE.search(sql)
    if match is None:
        return None

    result = execute_sql(db_id, sql)
    if not result["ok"] or not result["rows"] or not has_duplicate_rows(result["rows"]):
        return None

    repaired_sql = SIMPLE_SELECT_COLUMN_RE.sub(
        f"SELECT DISTINCT {match.group('column')} FROM",
        sql,
        count=1,
    )
    note = f"added DISTINCT for duplicate {match.group('column')} projection"
    return repaired_sql, note


def replace_string_comparison(
    sql: str,
    bad_alias: str,
    bad_column: str,
    new_alias: str,
    label_column: str,
    value: str,
) -> str:
    replaced = False

    def replace_match(match: re.Match) -> str:
        nonlocal replaced
        if replaced:
            return match.group(0)
        if (
            match.group("alias").lower() == bad_alias
            and match.group("column").lower() == bad_column
            and match.group("value").replace("''", "'").lower() == value.lower()
        ):
            replaced = True
            return f"{new_alias}.{label_column} = '{match.group('value')}'"
        return match.group(0)

    return STRING_COMPARISON_RE.sub(replace_match, sql)


def insert_join(sql: str, join_clause: str) -> str:
    clause_match = CLAUSE_START_RE.search(sql)
    if clause_match is None:
        return f"{sql} {join_clause}"

    insert_at = clause_match.start()
    before_clause = sql[:insert_at].rstrip()
    after_clause = sql[insert_at:].lstrip()
    return f"{before_clause} {join_clause} {after_clause}"


def replacement_alias_for_error(sql: str, error: str, schema: dict[str, set[str]]) -> tuple[str, str] | None:
    match = NO_SUCH_COLUMN_RE.search(error or "")
    if not match:
        return None

    bad_alias, column = split_column_reference(match.group("name"))
    if bad_alias is None:
        return None

    aliases = parse_aliases(sql)
    if bad_alias not in aliases:
        return None

    owner_aliases = build_owner_aliases(schema, aliases).get(column, [])
    owner_aliases = [alias for alias in owner_aliases if alias != bad_alias]

    if len(owner_aliases) != 1:
        return None

    return bad_alias, owner_aliases[0]


def undeclared_alias_repair_for_error(
    sql: str,
    error: str,
    schema: dict[str, set[str]],
) -> tuple[str, str, str, str] | None:
    """Replace a missing alias only when one in-scope table owns the column."""
    if has_nested_select(sql):
        return None

    match = NO_SUCH_COLUMN_RE.search(error or "")
    if not match:
        return None

    bad_alias, column = split_column_reference(match.group("name"))
    if bad_alias is None:
        return None

    aliases = parse_aliases(sql)
    if bad_alias in aliases:
        return None

    owner_aliases = build_owner_aliases(schema, aliases).get(column, [])
    if len(owner_aliases) != 1:
        return None

    owner_alias = owner_aliases[0]
    repaired_sql = replace_qualified_column_alias(sql, bad_alias, owner_alias, column)
    if repaired_sql == sql:
        return None
    return repaired_sql, bad_alias, owner_alias, column


def unqualified_column_repair_for_error(
    sql: str,
    error: str,
    schema: dict[str, set[str]],
) -> tuple[str, str, str] | None:
    """Qualify a bare missing column only when one joined alias can own it."""
    if has_nested_select(sql):
        return None

    match = NO_SUCH_COLUMN_RE.search(error or "")
    if not match:
        return None

    bad_alias, column = split_column_reference(match.group("name"))
    if bad_alias is not None:
        return None

    aliases = parse_aliases(sql)
    if len(aliases) < 2:
        return None

    owner_aliases = build_owner_aliases(schema, aliases).get(column, [])
    if len(owner_aliases) != 1:
        return None

    owner_alias = owner_aliases[0]
    repaired_sql = replace_unqualified_column(sql, column, owner_alias)
    if repaired_sql == sql:
        return None
    return repaired_sql, owner_alias, column


def replace_unqualified_column(sql: str, column: str, owner_alias: str) -> str:
    """Replace bare identifiers while leaving strings and qualified names alone."""
    identifier_re = re.compile(
        rf"(?P<quote>[`\"]?)(?P<column>{re.escape(column)})(?P=quote)(?![\w.]|\s*\.)",
        re.IGNORECASE,
    )
    parts = re.split(r"('(?:''|[^'])*')", sql)

    def replace_match(match: re.Match) -> str:
        prefix = match.string[: match.start()]
        if re.search(r"\.\s*$", prefix):
            return match.group(0)
        return f"{owner_alias}.{match.group('quote')}{match.group('column')}{match.group('quote')}"

    for index in range(0, len(parts), 2):
        parts[index] = identifier_re.sub(replace_match, parts[index])
    return "".join(parts)


def join_repair_for_error(sql: str, error: str, database_info: dict) -> tuple[str, str, str, str] | None:
    if has_nested_select(sql):
        return None

    match = NO_SUCH_COLUMN_RE.search(error or "")
    if not match:
        return None

    bad_alias, column = split_column_reference(match.group("name"))
    if bad_alias is None:
        return None

    aliases = parse_aliases(sql)
    if bad_alias not in aliases:
        return None

    schema = database_info["schema"]
    owner_aliases = build_owner_aliases(schema, aliases).get(column, [])
    if owner_aliases:
        return None

    owner_tables = owner_tables_for_column(schema, column)
    if len(owner_tables) != 1:
        return None

    missing_table = owner_tables[0]
    join = find_direct_join(aliases, missing_table, database_info["foreign_keys"])
    if join is None:
        return None

    existing_alias, existing_column, missing_column, _ = join
    new_alias = next_table_alias(aliases)
    join_clause = (
        f"INNER JOIN {missing_table} AS {new_alias} "
        f"ON {existing_alias}.{existing_column} = {new_alias}.{missing_column}"
    )
    repaired_sql = insert_join(sql, join_clause)
    repaired_sql = replace_qualified_column_alias(repaired_sql, bad_alias, new_alias.lower(), column)
    note = (
        f"added {missing_table} AS {new_alias} "
        f"ON {existing_alias}.{existing_column} = {new_alias}.{missing_column}; "
        f"{bad_alias}.{column} -> {new_alias}.{column}"
    )
    return repaired_sql, note, bad_alias, new_alias


def lookup_repair_for_sql(db_id: str, sql: str, database_info: dict) -> tuple[str, str] | None:
    if has_nested_select(sql):
        return None

    aliases = parse_aliases(sql)
    if not aliases:
        return None

    for match in STRING_COMPARISON_RE.finditer(sql):
        source_alias = match.group("alias").lower()
        source_column = match.group("column").lower()
        literal_value = match.group("value").replace("''", "'")
        source_table = aliases.get(source_alias)
        if source_table is None:
            continue

        target = find_foreign_key_target(source_table, source_column, database_info["foreign_keys"])
        if target is None:
            continue

        target_table, target_column = target
        if target_table in aliases.values():
            continue

        label_columns = matching_label_columns(db_id, target_table, literal_value, database_info)
        if len(label_columns) != 1:
            continue

        label_column = label_columns[0]
        new_alias = next_table_alias(aliases)
        join_clause = (
            f"INNER JOIN {target_table} AS {new_alias} "
            f"ON {source_alias}.{source_column} = {new_alias}.{target_column}"
        )
        repaired_sql = insert_join(sql, join_clause)
        repaired_sql = replace_string_comparison(
            repaired_sql,
            source_alias,
            source_column,
            new_alias,
            label_column,
            literal_value,
        )
        note = (
            f"added lookup {target_table} AS {new_alias} "
            f"ON {source_alias}.{source_column} = {new_alias}.{target_column}; "
            f"{source_alias}.{source_column} = '{literal_value}' -> "
            f"{new_alias}.{label_column} = '{literal_value}'"
        )
        return repaired_sql, note

    return None


def value_repair_for_sql(db_id: str, sql: str, database_info: dict) -> tuple[str, str] | None:
    if has_nested_select(sql):
        return None

    aliases = parse_aliases(sql)
    if not aliases:
        return None

    schema = database_info["schema"]

    for match in STRING_COMPARISON_RE.finditer(sql):
        source_alias = match.group("alias").lower()
        source_column = match.group("column").lower()
        literal_value = match.group("value").replace("''", "'")
        source_table = aliases.get(source_alias)
        if source_table is None:
            continue
        if source_column not in schema.get(source_table, set()):
            continue

        canonical_value = canonical_value_for_column(db_id, source_table, source_column, literal_value)
        if canonical_value is None:
            continue

        repaired_sql = replace_string_literal_for_column(
            sql,
            source_alias,
            source_column,
            literal_value,
            canonical_value,
        )
        note = (
            f"canonicalized {source_alias}.{source_column}: "
            f"'{literal_value}' -> '{canonical_value}'"
        )
        return repaired_sql, note

    return None


def replace_qualified_column_alias(sql: str, bad_alias: str, good_alias: str, column: str) -> str:
    def replace_match(match: re.Match) -> str:
        alias = match.group("alias")
        matched_column = match.group("column")
        quote = match.group("quote")
        if alias.lower() == bad_alias and matched_column.lower() == column:
            return f"{good_alias}.{quote}{matched_column}{quote}"
        return match.group(0)

    return QUALIFIED_COLUMN_RE.sub(replace_match, sql)


def repair_sql(
    db_id: str,
    sql: str,
    max_passes: int,
    database_info_cache: dict[str, dict],
    enable_join_repair: bool,
    enable_semantic_repair: bool,
) -> tuple[str, list[str]]:
    database_info = database_info_cache.setdefault(db_id, load_database_info(db_id))
    schema = database_info["schema"]
    repaired_sql = sql
    repair_notes = []

    for _ in range(max_passes):
        result = execute_sql(db_id, repaired_sql)
        if result["ok"]:
            if not enable_semantic_repair:
                break
            lookup_repair = lookup_repair_for_sql(db_id, repaired_sql, database_info)
            value_repair = None
            if lookup_repair is None:
                value_repair = value_repair_for_sql(db_id, repaired_sql, database_info)
            prune_repair = None
            if lookup_repair is None and value_repair is None:
                prune_repair = leading_join_prune_for_sql(repaired_sql)
            distinct_repair = None
            if lookup_repair is None and value_repair is None and prune_repair is None:
                distinct_repair = distinct_repair_for_sql(db_id, repaired_sql)
            semantic_repair = lookup_repair or value_repair or prune_repair or distinct_repair
            if semantic_repair is None:
                break
            next_sql, note = semantic_repair
            if next_sql == repaired_sql:
                break
            next_result = execute_sql(db_id, next_sql)
            if not next_result["ok"]:
                break
            repair_notes.append(note)
            repaired_sql = next_sql
            continue

        replacement = replacement_alias_for_error(repaired_sql, result["error"], schema)
        if replacement is None:
            undeclared_alias_repair = undeclared_alias_repair_for_error(
                repaired_sql,
                result["error"],
                schema,
            )
            if undeclared_alias_repair is not None:
                next_sql, bad_alias, owner_alias, column = undeclared_alias_repair
                repair_notes.append(f"{bad_alias}.{column} -> {owner_alias}.{column}")
                if next_sql == repaired_sql:
                    break
                repaired_sql = next_sql
                continue

            unqualified_repair = unqualified_column_repair_for_error(
                repaired_sql,
                result["error"],
                schema,
            )
            if unqualified_repair is not None:
                next_sql, owner_alias, column = unqualified_repair
                repair_notes.append(f"{column} -> {owner_alias}.{column}")
                if next_sql == repaired_sql:
                    break
                repaired_sql = next_sql
                continue

            join_repair = None
            if enable_join_repair:
                join_repair = join_repair_for_error(repaired_sql, result["error"], database_info)
            if join_repair is None:
                break
            next_sql, note, _, _ = join_repair
            repair_notes.append(note)
        else:
            bad_alias, good_alias = replacement
            _, column = split_column_reference(NO_SUCH_COLUMN_RE.search(result["error"]).group("name"))
            next_sql = replace_qualified_column_alias(repaired_sql, bad_alias, good_alias, column)
            repair_notes.append(f"{bad_alias}.{column} -> {good_alias}.{column}")

        if next_sql == repaired_sql:
            break

        repaired_sql = next_sql

    return repaired_sql, repair_notes


def repair_record(
    record: dict,
    max_passes: int,
    database_info_cache: dict[str, dict],
    enable_join_repair: bool,
    enable_semantic_repair: bool,
) -> dict:
    repaired_sql, repair_notes = repair_sql(
        record["db_id"],
        record["predicted_sql"],
        max_passes,
        database_info_cache,
        enable_join_repair,
        enable_semantic_repair,
    )
    return {
        **record,
        "original_predicted_sql": record["predicted_sql"],
        "predicted_sql": repaired_sql,
        "repair_applied": repaired_sql != record["predicted_sql"],
        "repair_notes": repair_notes,
        "exact_match": repaired_sql.strip() == record["expected_sql"].strip(),
    }


def main() -> None:
    args = parse_args()
    records = read_jsonl(args.input_path)
    database_info_cache: dict[str, dict] = {}
    repaired_records = [
        repair_record(
            record,
            args.max_passes,
            database_info_cache,
            not args.disable_join_repair,
            not args.disable_semantic_repair,
        )
        for record in records
    ]

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_path, repaired_records)

    repaired_count = sum(record["repair_applied"] for record in repaired_records)
    print(f"Loaded predictions: {len(records)}")
    print(f"Repaired predictions: {repaired_count}")
    print(f"Wrote repaired predictions: {args.output_path}")


if __name__ == "__main__":
    main()

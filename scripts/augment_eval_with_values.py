"""Add question-relevant SQLite values to text-to-SQL evaluation prompts.

The retriever only reads the natural-language prompt and the target database.
It never reads the expected SQL, which keeps the generated hints usable at
real inference time.
"""

import argparse
import json
import re
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASES_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "dev_databases"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "outputs" / "lora-run-012" / "eval_set_100.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "value-retrieval" / "eval_set_100.jsonl"
WORD_RE = re.compile(r"[A-Za-z0-9]+")
QUESTION_RE = re.compile(
    r"Question:\s*(.*?)(?=\n(?:Evidence:|Return only the SQL query\.))",
    re.DOTALL,
)
EVIDENCE_RE = re.compile(r"Evidence:\s*(.*?)(?=\n\nReturn only the SQL query\.)", re.DOTALL)
STOP_WORDS = {
    "a", "all", "an", "and", "are", "as", "at", "be", "by", "do", "does",
    "for", "from", "give", "how", "in", "include", "is", "list", "me", "of",
    "on", "or", "show", "that", "the", "their", "to", "was", "were", "what",
    "when", "where", "which", "who", "with", "write",
}


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def normalized_words(text: str) -> list[str]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text).replace("_", " ")
    return [word.casefold() for word in WORD_RE.findall(separated)]


def question_from_prompt(prompt: str) -> str:
    match = QUESTION_RE.search(prompt)
    if match is None:
        raise ValueError("Prompt does not contain a Question section")
    return match.group(1).strip()


def retrieval_text_from_prompt(prompt: str) -> str:
    """Use only inference-visible question and evidence text for retrieval."""
    question = question_from_prompt(prompt)
    evidence_match = EVIDENCE_RE.search(prompt)
    if evidence_match is None:
        return question
    return f"{question} {evidence_match.group(1).strip()}"


def contains_word_sequence(container: list[str], sequence: list[str]) -> bool:
    if not sequence or len(sequence) > len(container):
        return False
    width = len(sequence)
    return any(container[index : index + width] == sequence for index in range(len(container) - width + 1))


def value_score(value: object, question: str, column: str) -> float:
    """Score a database value without using the expected SQL."""
    value_text = str(value).strip()
    if not value_text or len(value_text) > 100:
        return 0.0

    value_words = normalized_words(value_text)
    question_words = normalized_words(question)
    if not value_words:
        return 0.0

    meaningful_value_words = {word for word in value_words if word not in STOP_WORDS}
    meaningful_question_words = {word for word in question_words if word not in STOP_WORDS}
    ordered_column_words = [word for word in normalized_words(column) if word not in STOP_WORDS]
    column_words = set(ordered_column_words)
    column_overlap = column_words & meaningful_question_words
    if not meaningful_value_words or not contains_word_sequence(question_words, value_words):
        return 0.0

    is_numeric = all(word.isdigit() for word in value_words)
    is_short = len("".join(value_words)) <= 2
    if (is_numeric or is_short) and not contains_word_sequence(question_words, ordered_column_words):
        return 0.0

    value_normalized = " ".join(value_words)
    return 100.0 + min(len(value_normalized), 30) + 3.0 * len(column_overlap)


@lru_cache(maxsize=None)
def scan_database_values(
    sqlite_path: Path,
    distinct_scan_limit: int,
) -> tuple[tuple[str, str, str], ...]:
    """Scan each database once, then reuse its values for every question."""
    scanned: list[tuple[str, str, str]] = []
    with closing(sqlite3.connect(sqlite_path)) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in tables:
            columns = [row[1] for row in connection.execute(f"PRAGMA table_info({quote_identifier(table)})")]
            for column in columns:
                sql = (
                    f"SELECT DISTINCT {quote_identifier(column)} "
                    f"FROM {quote_identifier(table)} "
                    f"WHERE {quote_identifier(column)} IS NOT NULL "
                    f"LIMIT {int(distinct_scan_limit)}"
                )
                try:
                    values = [row[0] for row in connection.execute(sql)]
                except sqlite3.Error:
                    continue

                scanned.extend(
                    (f"{table}.{column}", column, str(value).strip())
                    for value in values
                    if not isinstance(value, bytes) and str(value).strip()
                )
    return tuple(scanned)


def database_values(
    sqlite_path: Path,
    question: str,
    max_columns: int = 8,
    max_values_per_column: int = 5,
    distinct_scan_limit: int = 1000,
) -> list[str]:
    """Return compact table.column value hints ranked by question relevance."""
    by_column: dict[str, list[tuple[float, str]]] = {}
    for qualified_column, column, value in scan_database_values(sqlite_path, distinct_scan_limit):
        score = value_score(value, question, column)
        if score >= 20.0:
            by_column.setdefault(qualified_column, []).append((score, value))

    candidates: list[tuple[float, str, list[str]]] = []
    for qualified_column, scored_values in by_column.items():
        scored_values.sort(key=lambda item: (-item[0], item[1].casefold()))
        candidates.append(
            (
                scored_values[0][0],
                qualified_column,
                [value for _, value in scored_values[:max_values_per_column]],
            )
        )

    candidates.sort(key=lambda item: (-item[0], item[1].casefold()))
    return [
        f"{qualified_column}: " + ", ".join(repr(value) for value in values)
        for _, qualified_column, values in candidates[:max_columns]
    ]


def add_value_hints(prompt: str, hints: list[str]) -> str:
    if not hints:
        return prompt
    marker = "\n\nReturn only the SQL query."
    if marker not in prompt:
        raise ValueError("Prompt does not contain the SQL return instruction")
    value_section = "\n\nRelevant database values:\n" + "\n".join(hints)
    return prompt.replace(marker, value_section + marker, 1)


def augment_record(record: dict) -> dict:
    sqlite_path = DATABASES_DIR / record["db_id"] / f"{record['db_id']}.sqlite"
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    retrieval_text = retrieval_text_from_prompt(record["prompt"])
    hints = database_values(sqlite_path, retrieval_text)
    return {
        **record,
        "prompt": add_value_hints(record["prompt"], hints),
        "prompt_style": f"{record.get('prompt_style', 'unknown')}_values_v1",
        "retrieved_value_hints": hints,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add relevant SQLite values to eval prompts.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = read_jsonl(args.input_path)
    augmented = [augment_record(record) for record in records]
    write_jsonl(args.output_path, augmented)
    hint_count = sum(len(record["retrieved_value_hints"]) for record in augmented)
    records_with_hints = sum(bool(record["retrieved_value_hints"]) for record in augmented)
    print(f"Records: {len(augmented)}")
    print(f"Records with value hints: {records_with_hints}")
    print(f"Value-hint lines: {hint_count}")
    print(f"Wrote: {args.output_path}")


if __name__ == "__main__":
    main()

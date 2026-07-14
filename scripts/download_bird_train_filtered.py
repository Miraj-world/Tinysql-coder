"""Download the curated BIRD-SQL training pairs and compact schema metadata.

The full BIRD database archive is almost 9 GB. This experiment only needs the
verified question/SQL pairs and column metadata, so it deliberately avoids that
large download.
"""

import json
import shutil
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import hf_hub_download


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "bird_train_filtered"
TRAIN_OUTPUT_PATH = OUTPUT_DIR / "train.jsonl"
COLUMN_MEANING_OUTPUT_PATH = OUTPUT_DIR / "train_column_meaning.json"
TABLE_SCHEMA_OUTPUT_PATH = OUTPUT_DIR / "train_tables.json"

DATASET_NAME = "birdsql/bird23-train-filtered"
DATASET_REVISION = "4068469807b255fcfc0816bdd520946fe460d256"
SCHEMA_MIRROR_NAME = "Deema/BIRD-SQL"
SCHEMA_MIRROR_REVISION = "c4a98a189f3b5af9809f5f308d03d91fe6cf87d5"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for row in rows:
            output_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def download_dataset() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(
        DATASET_NAME,
        split="train",
        revision=DATASET_REVISION,
    )
    rows = [dict(row) for row in dataset]
    db_ids = {row["db_id"] for row in rows}
    write_jsonl(TRAIN_OUTPUT_PATH, rows)

    cached_column_meaning = Path(
        hf_hub_download(
            repo_id=DATASET_NAME,
            filename="train_column_meaning.json",
            repo_type="dataset",
            revision=DATASET_REVISION,
        )
    )
    shutil.copyfile(cached_column_meaning, COLUMN_MEANING_OUTPUT_PATH)

    cached_table_schema = Path(
        hf_hub_download(
            repo_id=SCHEMA_MIRROR_NAME,
            filename="train_tables.json",
            repo_type="dataset",
            revision=SCHEMA_MIRROR_REVISION,
        )
    )
    shutil.copyfile(cached_table_schema, TABLE_SCHEMA_OUTPUT_PATH)

    table_schemas = json.loads(TABLE_SCHEMA_OUTPUT_PATH.read_text(encoding="utf-8"))
    schema_db_ids = {schema["db_id"] for schema in table_schemas}
    if db_ids != schema_db_ids:
        raise ValueError(
            "Training rows and table schemas cover different databases: "
            f"missing={sorted(db_ids - schema_db_ids)}, extra={sorted(schema_db_ids - db_ids)}"
        )

    print(f"Downloaded curated training rows: {len(rows)}")
    print(f"Training databases: {len(db_ids)}")
    print(f"Rows: {TRAIN_OUTPUT_PATH}")
    print(f"Column metadata: {COLUMN_MEANING_OUTPUT_PATH}")
    print(f"Table/foreign-key schemas: {TABLE_SCHEMA_OUTPUT_PATH}")


if __name__ == "__main__":
    download_dataset()

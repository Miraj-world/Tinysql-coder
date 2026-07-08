from collections import Counter
from pathlib import Path

from datasets import Dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATASET_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "raw" / "bird-original.arrow"
DATABASES_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "dev_databases"


def expected_database_ids() -> list[str]:
    dataset = Dataset.from_file(str(RAW_DATASET_PATH))
    counts = Counter(row["db_id"] for row in dataset)
    return sorted(counts)


def existing_database_ids() -> set[str]:
    if not DATABASES_DIR.exists():
        return set()

    return {
        path.name
        for path in DATABASES_DIR.iterdir()
        if path.is_dir()
    }


def main() -> None:
    expected_ids = expected_database_ids()
    existing_ids = existing_database_ids()
    missing_ids = [db_id for db_id in expected_ids if db_id not in existing_ids]

    print(f"Expected databases: {len(expected_ids)}")
    for db_id in expected_ids:
        status = "found" if db_id in existing_ids else "missing"
        print(f"  {db_id}: {status}")

    print()
    print(f"Database folder expected at: {DATABASES_DIR}")

    if missing_ids:
        print()
        print("Missing schema/database folders:")
        for db_id in missing_ids:
            print(f"  {db_id}")
        print()
        print("Next action: download the official BIRD Mini-Dev complete package")
        print("and place/extract its dev_databases folder here:")
        print(f"  {DATABASES_DIR}")
    else:
        print()
        print("All expected database folders are present.")


if __name__ == "__main__":
    main()

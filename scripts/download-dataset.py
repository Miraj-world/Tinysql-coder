"""Download the BIRD Mini-Dev question/SQL rows from Hugging Face.

This gives us the benchmark examples, but not the full database schemas.
The matching SQLite databases come from the official Mini-Dev package.
"""

from pathlib import Path

from datasets import load_dataset

DATASET_NAME = "birdsql/bird_mini_dev"
SPLIT_NAME = "mini_dev_sqlite"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "bird_mini_dev"


def download_dataset() -> None:
    print(f"Downloading {DATASET_NAME} split '{SPLIT_NAME}'...")
    dataset = load_dataset(DATASET_NAME, split=SPLIT_NAME)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset.save_to_disk(str(OUTPUT_DIR))

    print(f"Saved {len(dataset)} rows to {OUTPUT_DIR}")
    print("Sample row:")
    print(dataset[0])


if __name__ == "__main__":
    download_dataset()

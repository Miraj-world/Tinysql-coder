"""Check whether the local setup is ready for the first fine-tuning run.

This verifies SFT files, tokenizer compatibility, token lengths, and whether
PyTorch can see CUDA. It prevents starting an expensive training run blindly.
"""

import json
import argparse
from pathlib import Path
from statistics import mean

import torch
from transformers import AutoTokenizer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "huggingface"
SFT_DIR = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft"
TRAIN_SFT_PATH = SFT_DIR / "train_sft.jsonl"
VALIDATION_SFT_PATH = SFT_DIR / "validation_sft.jsonl"

MAX_SEQUENCE_LENGTH_CANDIDATES = [1024, 1536, 2048, 4096]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check readiness for a LoRA training run.")
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--train-path", type=Path, default=TRAIN_SFT_PATH)
    parser.add_argument("--validation-path", type=Path, default=VALIDATION_SFT_PATH)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8") as input_file:
        return sum(1 for line in input_file if line.strip())


def check_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")


def format_messages(tokenizer: AutoTokenizer, example: dict) -> str:
    return tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )


def token_lengths(tokenizer: AutoTokenizer, examples: list[dict]) -> list[int]:
    lengths = []
    for example in examples:
        text = format_messages(tokenizer, example)
        token_ids = tokenizer(text, add_special_tokens=False)["input_ids"]
        lengths.append(len(token_ids))
    return lengths


def print_token_length_summary(lengths: list[int]) -> None:
    """Show whether examples fit common max sequence length choices."""
    sorted_lengths = sorted(lengths)
    p95_index = int(len(sorted_lengths) * 0.95) - 1
    p95_index = max(0, min(p95_index, len(sorted_lengths) - 1))

    print("Token length summary:")
    print(f"  examples: {len(lengths)}")
    print(f"  min: {min(lengths)}")
    print(f"  avg: {mean(lengths):.1f}")
    print(f"  p95: {sorted_lengths[p95_index]}")
    print(f"  max: {max(lengths)}")

    print("\nMax sequence length candidates:")
    for candidate in MAX_SEQUENCE_LENGTH_CANDIDATES:
        covered = sum(length <= candidate for length in lengths)
        print(f"  {candidate}: covers {covered}/{len(lengths)} examples")


def print_cuda_summary() -> None:
    """Report whether training can use the NVIDIA GPU from this environment."""
    print("PyTorch / CUDA:")
    print(f"  torch version: {torch.__version__}")
    print(f"  torch CUDA build: {torch.version.cuda}")
    print(f"  cuda available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"  cuda device count: {torch.cuda.device_count()}")
        print(f"  cuda device 0: {torch.cuda.get_device_name(0)}")
    else:
        print("  training device: CPU only")
        print("  note: this machine has an NVIDIA GPU, but this Python environment has CPU-only PyTorch.")


def main() -> None:
    args = parse_args()
    check_file(args.train_path)
    check_file(args.validation_path)

    train_count = count_lines(args.train_path)
    validation_count = count_lines(args.validation_path)

    print("SFT files:")
    print(f"  train: {train_count} examples -> {args.train_path}")
    print(f"  validation: {validation_count} examples -> {args.validation_path}")
    print()

    print_cuda_summary()
    print()

    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        cache_dir=MODEL_CACHE_DIR,
        trust_remote_code=True,
    )

    print(f"Model: {args.model}")
    train_examples = read_jsonl(args.train_path)
    validation_examples = read_jsonl(args.validation_path)
    lengths = token_lengths(tokenizer, train_examples + validation_examples)
    print_token_length_summary(lengths)

    print("\nRecommendation:")
    if torch.cuda.is_available():
        print("  You can start a small LoRA fine-tuning run.")
    else:
        print("  Do not start full training yet. Install a CUDA-enabled PyTorch build first, or run only tiny CPU smoke tests.")


if __name__ == "__main__":
    main()

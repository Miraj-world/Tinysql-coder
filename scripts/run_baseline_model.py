"""Run a base model on the fixed baseline evaluation set.

This is not fine-tuning. It measures how well the untrained base model performs
so later we can compare fine-tuned results against a real baseline.
"""

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_SET_PATH = PROJECT_ROOT / "outputs" / "baseline" / "baseline_eval_set.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "baseline"
OUTPUT_PATH = OUTPUT_DIR / "baseline_predictions.jsonl"
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "huggingface"

MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
MAX_NEW_TOKENS = 256


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for example in examples:
            output_file.write(json.dumps(example, ensure_ascii=False) + "\n")


def build_messages(prompt: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": "You are a careful text-to-SQL assistant. Return only SQL, with no markdown.",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]


def load_model(model_name: str) -> tuple[AutoTokenizer, AutoModelForCausalLM, torch.device]:
    """Load the model from the project-local Hugging Face cache."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float16 if device.type == "cuda" else torch.float32
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=MODEL_CACHE_DIR,
        trust_remote_code=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        cache_dir=MODEL_CACHE_DIR,
        dtype=dtype,
        trust_remote_code=True,
    )
    model.to(device)
    model.eval()

    return tokenizer, model, device


def generate_sql(
    tokenizer: AutoTokenizer,
    model: AutoModelForCausalLM,
    device: torch.device,
    prompt: str,
) -> str:
    messages = build_messages(prompt)
    chat_prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(chat_prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
    return clean_generated_sql(tokenizer.decode(generated_ids, skip_special_tokens=True))


def clean_generated_sql(text: str) -> str:
    """Remove common markdown fences so evaluation sees only SQL text."""
    stripped = text.strip()

    if stripped.startswith("```sql"):
        stripped = stripped.removeprefix("```sql").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()

    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```").strip()

    return stripped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    eval_records = read_jsonl(EVAL_SET_PATH)

    if args.limit is not None:
        eval_records = eval_records[: args.limit]

    tokenizer, model, device = load_model(args.model)

    print(f"Model: {args.model}")
    print(f"Model cache: {MODEL_CACHE_DIR}")
    print(f"Device: {device}")
    print(f"Examples: {len(eval_records)}")

    predictions = []
    for index, record in enumerate(eval_records, start=1):
        predicted_sql = generate_sql(tokenizer, model, device, record["prompt"])
        result = {
            **record,
            "model": args.model,
            "predicted_sql": predicted_sql,
            "exact_match": predicted_sql.strip() == record["expected_sql"].strip(),
        }
        predictions.append(result)

        print(f"\nExample {index}/{len(eval_records)}")
        print(f"Question ID: {record['question_id']}")
        print(f"Difficulty: {record['difficulty']}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"Exact match: {result['exact_match']}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUTPUT_PATH, predictions)
    exact_matches = sum(record["exact_match"] for record in predictions)

    print(f"\nWrote predictions to {OUTPUT_PATH}")
    print(f"Exact matches: {exact_matches}/{len(predictions)}")


if __name__ == "__main__":
    main()

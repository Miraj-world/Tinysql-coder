"""Run a model on the fixed baseline evaluation set.

By default this measures the untrained base model. With ``--adapter-path`` it
loads a local LoRA adapter on top of the base model so we can compare the
fine-tuned model against the same baseline evaluation set.
"""

import argparse
import json
import re
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_SET_PATH = PROJECT_ROOT / "outputs" / "baseline" / "baseline_eval_set.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "baseline"
OUTPUT_PATH = OUTPUT_DIR / "baseline_predictions.jsonl"
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "huggingface"

MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
MAX_NEW_TOKENS = 256
SQL_START_RE = re.compile(r"\b(?:SELECT|WITH)\b", re.IGNORECASE)


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


def load_model(
    model_name: str,
    adapter_path: Path | None,
    load_in_4bit: bool = False,
) -> tuple[AutoTokenizer, AutoModelForCausalLM, torch.device]:
    """Load the base model and optionally attach a local LoRA adapter."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float16 if device.type == "cuda" else torch.float32
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=MODEL_CACHE_DIR,
        trust_remote_code=True,
    )
    model_kwargs = {
        "cache_dir": MODEL_CACHE_DIR,
        "dtype": dtype,
        "trust_remote_code": True,
    }
    if load_in_4bit:
        model_kwargs.update(
            {
                "quantization_config": BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch.float16,
                ),
                "device_map": {"": 0},
            }
        )

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    if adapter_path is not None:
        if not adapter_path.exists():
            raise FileNotFoundError(f"LoRA adapter not found: {adapter_path}")

        model = PeftModel.from_pretrained(model, adapter_path)

    if not load_in_4bit:
        model.to(device)
    model.eval()

    return tokenizer, model, device


def generate_sql(
    tokenizer: AutoTokenizer,
    model: AutoModelForCausalLM,
    device: torch.device,
    prompt: str,
    num_beams: int = 1,
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
            num_beams=num_beams,
            early_stopping=num_beams > 1,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
    return clean_generated_sql(tokenizer.decode(generated_ids, skip_special_tokens=True))


def clean_generated_sql(text: str) -> str:
    """Remove common markdown fences so evaluation sees only SQL text."""
    stripped = text.strip()

    if "FINAL_SQL:" in stripped:
        stripped = stripped.split("FINAL_SQL:", maxsplit=1)[1].strip()

    sql_start = SQL_START_RE.search(stripped)
    if sql_start is not None:
        stripped = stripped[sql_start.start() :].strip()

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
    parser.add_argument("--eval-set-path", type=Path, default=EVAL_SET_PATH)
    parser.add_argument("--adapter-path", type=Path, default=None)
    parser.add_argument("--output-path", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--num-beams", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.num_beams < 1:
        raise ValueError("--num-beams must be at least 1")
    eval_records = read_jsonl(args.eval_set_path)

    if args.limit is not None:
        eval_records = eval_records[: args.limit]

    tokenizer, model, device = load_model(args.model, args.adapter_path, args.load_in_4bit)

    print(f"Model: {args.model}")
    print(f"Adapter: {args.adapter_path if args.adapter_path else 'none'}")
    print(f"Model cache: {MODEL_CACHE_DIR}")
    print(f"Device: {device}")
    print(f"4-bit: {args.load_in_4bit}")
    print(f"Beams: {args.num_beams}")
    print(f"Examples: {len(eval_records)}")

    predictions = []
    for index, record in enumerate(eval_records, start=1):
        predicted_sql = generate_sql(tokenizer, model, device, record["prompt"], args.num_beams)
        result = {
            **record,
            "model": args.model,
            "adapter_path": str(args.adapter_path) if args.adapter_path else None,
            "predicted_sql": predicted_sql,
            "exact_match": predicted_sql.strip() == record["expected_sql"].strip(),
        }
        predictions.append(result)

        print(f"\nExample {index}/{len(eval_records)}")
        print(f"Question ID: {record['question_id']}")
        print(f"Difficulty: {record['difficulty']}")
        print(f"Predicted SQL: {predicted_sql}")
        print(f"Exact match: {result['exact_match']}")

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_path, predictions)
    exact_matches = sum(record["exact_match"] for record in predictions)

    print(f"\nWrote predictions to {args.output_path}")
    print(f"Exact matches: {exact_matches}/{len(predictions)}")


if __name__ == "__main__":
    main()

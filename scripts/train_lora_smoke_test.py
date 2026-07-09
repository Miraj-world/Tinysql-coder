"""Run a tiny LoRA training smoke test on the SFT data.

This is intentionally not a real training run. It proves that CUDA, tokenization,
LoRA adapter setup, loss computation, backpropagation, and adapter saving all
work before we spend time on a longer fine-tune.
"""

import json
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from torch.optim import AdamW
from transformers import AutoModelForCausalLM, AutoTokenizer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "huggingface"
TRAIN_SFT_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft" / "train_sft.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "models" / "lora-smoke-test"

MAX_SEQUENCE_LENGTH = 2048
SMOKE_TEST_EXAMPLES = 4
TRAINING_STEPS = 2
LEARNING_RATE = 2e-4


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def format_example(tokenizer: AutoTokenizer, example: dict) -> str:
    return tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )


def tokenize_examples(tokenizer: AutoTokenizer, examples: list[dict]) -> dict[str, torch.Tensor]:
    texts = [format_example(tokenizer, example) for example in examples]
    tokenized = tokenizer(
        texts,
        max_length=MAX_SEQUENCE_LENGTH,
        truncation=True,
        padding=True,
        return_tensors="pt",
    )

    # Causal language modeling learns to predict the next token.
    # Labels are the same tokens, with padding masked out as -100.
    labels = tokenized["input_ids"].clone()
    labels[tokenized["attention_mask"] == 0] = -100
    tokenized["labels"] = labels
    return tokenized


def load_tokenizer() -> AutoTokenizer:
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        cache_dir=MODEL_CACHE_DIR,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return tokenizer


def load_lora_model() -> torch.nn.Module:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        cache_dir=MODEL_CACHE_DIR,
        dtype=torch.float16,
        trust_remote_code=True,
    )

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this smoke test. Run scripts/check_training_readiness.py.")

    device = torch.device("cuda")
    print(f"Using device: {torch.cuda.get_device_name(0)}")

    tokenizer = load_tokenizer()
    model = load_lora_model().to(device)
    model.train()

    examples = read_jsonl(TRAIN_SFT_PATH)[:SMOKE_TEST_EXAMPLES]
    batch = tokenize_examples(tokenizer, examples)
    batch = {key: value.to(device) for key, value in batch.items()}

    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE)

    for step in range(1, TRAINING_STEPS + 1):
        optimizer.zero_grad(set_to_none=True)
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        optimizer.step()

        print(f"step {step}/{TRAINING_STEPS} - loss: {loss.item():.4f}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Saved smoke-test LoRA adapter to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

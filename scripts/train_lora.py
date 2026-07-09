"""Train the first real LoRA adapter for TinySQL-coder.

This script is the step after the smoke test. The smoke test proved that CUDA,
LoRA, tokenization, and saving all work. This script uses the full SFT training
file and periodically checks validation loss so we can tell whether training is
actually learning.
"""

import argparse
import json
import math
import random
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "huggingface"

TRAIN_SFT_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft" / "train_sft.jsonl"
VALIDATION_SFT_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft" / "validation_sft.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "models" / "tinysql-coder-lora"

MAX_SEQUENCE_LENGTH = 2048
SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a LoRA adapter on BIRD Mini-Dev SFT data.")
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--eval-every", type=int, default=10)
    parser.add_argument("--validation-limit", type=int, default=25)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def seed_everything(seed: int) -> None:
    """Make the small training run easier to compare across reruns."""
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


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

    # Gradient checkpointing reduces GPU memory usage. It can make training a
    # little slower, but that is a good tradeoff on a laptop GPU.
    model.gradient_checkpointing_enable()
    model.config.use_cache = False

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


def format_full_conversation(tokenizer: AutoTokenizer, example: dict) -> str:
    """Format system + user + assistant messages exactly as Qwen expects."""
    return tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )


def format_prompt_only(tokenizer: AutoTokenizer, example: dict) -> str:
    """Format the input side without the gold SQL answer.

    We use this text length to mask the prompt tokens in the labels. That means
    the loss only trains the assistant SQL answer.
    """
    return tokenizer.apply_chat_template(
        example["messages"][:-1],
        tokenize=False,
        add_generation_prompt=True,
    )


def tokenize_example(tokenizer: AutoTokenizer, example: dict) -> dict[str, list[int]]:
    full_text = format_full_conversation(tokenizer, example)
    prompt_text = format_prompt_only(tokenizer, example)

    full_tokens = tokenizer(
        full_text,
        add_special_tokens=False,
        max_length=MAX_SEQUENCE_LENGTH,
        truncation=True,
    )
    prompt_tokens = tokenizer(prompt_text, add_special_tokens=False)

    input_ids = full_tokens["input_ids"]
    attention_mask = full_tokens["attention_mask"]

    # Labels start as a copy of input_ids. Then we hide the prompt tokens with
    # -100 because PyTorch ignores -100 when computing language-model loss.
    labels = input_ids.copy()
    prompt_length = min(len(prompt_tokens["input_ids"]), len(labels))
    labels[:prompt_length] = [-100] * prompt_length

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


def tokenize_dataset(tokenizer: AutoTokenizer, examples: list[dict]) -> list[dict[str, list[int]]]:
    tokenized_examples = [tokenize_example(tokenizer, example) for example in examples]

    # If an example is so long that the assistant answer was fully truncated,
    # there are no useful label tokens left. Drop it instead of training on it.
    return [
        example
        for example in tokenized_examples
        if any(label != -100 for label in example["labels"])
    ]


def collate_batch(tokenizer: AutoTokenizer, examples: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
    max_length = max(len(example["input_ids"]) for example in examples)
    pad_token_id = tokenizer.pad_token_id

    batch = {
        "input_ids": [],
        "attention_mask": [],
        "labels": [],
    }

    for example in examples:
        padding_length = max_length - len(example["input_ids"])
        batch["input_ids"].append(example["input_ids"] + [pad_token_id] * padding_length)
        batch["attention_mask"].append(example["attention_mask"] + [0] * padding_length)
        batch["labels"].append(example["labels"] + [-100] * padding_length)

    return {
        key: torch.tensor(value, dtype=torch.long)
        for key, value in batch.items()
    }


def move_batch_to_device(batch: dict[str, torch.Tensor], device: torch.device) -> dict[str, torch.Tensor]:
    return {key: value.to(device) for key, value in batch.items()}


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    dataloader: DataLoader,
    device: torch.device,
    validation_limit: int,
) -> float:
    """Return average validation loss over a small validation slice."""
    model.eval()
    losses = []

    for batch_index, batch in enumerate(dataloader, start=1):
        if batch_index > validation_limit:
            break

        batch = move_batch_to_device(batch, device)
        outputs = model(**batch)
        losses.append(outputs.loss.item())

    model.train()
    return sum(losses) / len(losses)


def main() -> None:
    args = parse_args()
    seed_everything(SEED)

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required. Run scripts/check_training_readiness.py first.")

    device = torch.device("cuda")
    print(f"Using device: {torch.cuda.get_device_name(0)}")
    print(f"Max steps: {args.max_steps}")
    print(f"Gradient accumulation steps: {args.gradient_accumulation_steps}")

    tokenizer = load_tokenizer()
    train_examples = read_jsonl(TRAIN_SFT_PATH)
    validation_examples = read_jsonl(VALIDATION_SFT_PATH)

    print(f"Raw train examples: {len(train_examples)}")
    print(f"Raw validation examples: {len(validation_examples)}")

    train_dataset = tokenize_dataset(tokenizer, train_examples)
    validation_dataset = tokenize_dataset(tokenizer, validation_examples)

    print(f"Tokenized train examples: {len(train_dataset)}")
    print(f"Tokenized validation examples: {len(validation_dataset)}")

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda examples: collate_batch(tokenizer, examples),
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=1,
        shuffle=False,
        collate_fn=lambda examples: collate_batch(tokenizer, examples),
    )

    model = load_lora_model().to(device)
    model.train()

    optimizer = AdamW(model.parameters(), lr=args.learning_rate)
    optimizer.zero_grad(set_to_none=True)

    step = 0
    micro_step = 0
    running_loss = 0.0
    batches_per_epoch = math.ceil(len(train_dataset) / args.batch_size)

    while step < args.max_steps:
        for batch in train_loader:
            micro_step += 1
            batch = move_batch_to_device(batch, device)

            outputs = model(**batch)
            loss = outputs.loss / args.gradient_accumulation_steps
            loss.backward()
            running_loss += loss.item()

            if micro_step % args.gradient_accumulation_steps == 0:
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)

                step += 1
                train_loss = running_loss
                running_loss = 0.0

                print(f"step {step}/{args.max_steps} - train loss: {train_loss:.4f}")

                if step % args.eval_every == 0 or step == args.max_steps:
                    validation_loss = evaluate(
                        model,
                        validation_loader,
                        device,
                        args.validation_limit,
                    )
                    print(f"step {step}/{args.max_steps} - validation loss: {validation_loss:.4f}")

                if step >= args.max_steps:
                    break

        print(f"Completed pass over train loader ({batches_per_epoch} batches).")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved LoRA adapter to: {args.output_dir}")


if __name__ == "__main__":
    main()

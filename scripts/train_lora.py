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
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
MODEL_CACHE_DIR = PROJECT_ROOT / "models" / "huggingface"

TRAIN_SFT_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft" / "train_sft.jsonl"
VALIDATION_SFT_PATH = PROJECT_ROOT / "data" / "bird_mini_dev" / "sft" / "validation_sft.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "models" / "tinysql-coder-lora"

DEFAULT_MAX_SEQUENCE_LENGTH = 2048
SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a LoRA adapter on BIRD Mini-Dev SFT data.")
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--eval-every", type=int, default=10)
    parser.add_argument("--validation-limit", type=int, default=25)
    parser.add_argument("--max-sequence-length", type=int, default=DEFAULT_MAX_SEQUENCE_LENGTH)
    parser.add_argument("--train-path", type=Path, default=TRAIN_SFT_PATH)
    parser.add_argument("--validation-path", type=Path, default=VALIDATION_SFT_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--load-in-4bit",
        action="store_true",
        help="Load the base model in NF4 and train a QLoRA adapter.",
    )
    parser.add_argument(
        "--drop-overlength",
        action="store_true",
        help="Drop examples longer than the sequence limit instead of truncating gold SQL.",
    )
    parser.add_argument(
        "--initial-adapter-path",
        type=Path,
        default=None,
        help="Continue training from an existing LoRA adapter instead of creating a new one.",
    )
    return parser.parse_args()


def seed_everything(seed: int) -> None:
    """Make the small training run easier to compare across reruns."""
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def load_tokenizer(model_name: str) -> AutoTokenizer:
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=MODEL_CACHE_DIR,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return tokenizer


def load_lora_model(
    model_name: str,
    initial_adapter_path: Path | None = None,
    load_in_4bit: bool = False,
) -> torch.nn.Module:
    model_kwargs = {
        "cache_dir": MODEL_CACHE_DIR,
        "dtype": torch.float16,
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

    # Gradient checkpointing reduces GPU memory usage. It can make training a
    # little slower, but that is a good tradeoff on a laptop GPU.
    if load_in_4bit:
        model = prepare_model_for_kbit_training(
            model,
            use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
        )
    else:
        model.gradient_checkpointing_enable()
    model.config.use_cache = False

    if initial_adapter_path is not None:
        if not initial_adapter_path.exists():
            raise FileNotFoundError(f"Initial LoRA adapter not found: {initial_adapter_path}")
        model = PeftModel.from_pretrained(model, initial_adapter_path, is_trainable=True)
        model.print_trainable_parameters()
        return model

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


def tokenize_example(
    tokenizer: AutoTokenizer,
    example: dict,
    max_sequence_length: int,
) -> dict[str, list[int]]:
    full_text = format_full_conversation(tokenizer, example)
    prompt_text = format_prompt_only(tokenizer, example)

    full_tokens = tokenizer(
        full_text,
        add_special_tokens=False,
        max_length=max_sequence_length,
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


def tokenize_dataset(
    tokenizer: AutoTokenizer,
    examples: list[dict],
    max_sequence_length: int,
    drop_overlength: bool = False,
) -> list[dict[str, list[int]]]:
    tokenized_examples = []
    for example in examples:
        if drop_overlength:
            full_text = format_full_conversation(tokenizer, example)
            full_length = len(tokenizer(full_text, add_special_tokens=False)["input_ids"])
            if full_length > max_sequence_length:
                continue
        tokenized_examples.append(tokenize_example(tokenizer, example, max_sequence_length))

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
    print(f"Base model: {args.model}")
    print(f"Max steps: {args.max_steps}")
    print(f"Gradient accumulation steps: {args.gradient_accumulation_steps}")
    print(f"Max sequence length: {args.max_sequence_length}")
    print(f"Train path: {args.train_path}")
    print(f"Validation path: {args.validation_path}")
    print(f"Initial adapter: {args.initial_adapter_path if args.initial_adapter_path else 'none'}")
    print(f"4-bit QLoRA: {args.load_in_4bit}")
    print(f"Drop overlength examples: {args.drop_overlength}")

    tokenizer = load_tokenizer(args.model)
    train_examples = read_jsonl(args.train_path)
    validation_examples = read_jsonl(args.validation_path)

    print(f"Raw train examples: {len(train_examples)}")
    print(f"Raw validation examples: {len(validation_examples)}")

    train_dataset = tokenize_dataset(
        tokenizer,
        train_examples,
        args.max_sequence_length,
        args.drop_overlength,
    )
    validation_dataset = tokenize_dataset(
        tokenizer,
        validation_examples,
        args.max_sequence_length,
        args.drop_overlength,
    )

    print(f"Tokenized train examples: {len(train_dataset)}")
    print(f"Tokenized validation examples: {len(validation_dataset)}")
    print(f"Dropped train examples: {len(train_examples) - len(train_dataset)}")
    print(f"Dropped validation examples: {len(validation_examples) - len(validation_dataset)}")

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

    model = load_lora_model(
        args.model,
        args.initial_adapter_path,
        args.load_in_4bit,
    )
    if not args.load_in_4bit:
        model = model.to(device)
    model.train()

    trainable_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = AdamW(trainable_parameters, lr=args.learning_rate)
    optimizer.zero_grad(set_to_none=True)

    step = 0
    micro_step = 0
    running_loss = 0.0
    batches_per_epoch = math.ceil(len(train_dataset) / args.batch_size)
    best_validation_loss = math.inf
    best_step = None
    final_validation_loss = None

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
                    final_validation_loss = validation_loss
                    print(f"step {step}/{args.max_steps} - validation loss: {validation_loss:.4f}")

                    if validation_loss < best_validation_loss:
                        best_validation_loss = validation_loss
                        best_step = step
                        args.output_dir.mkdir(parents=True, exist_ok=True)
                        model.save_pretrained(args.output_dir)
                        tokenizer.save_pretrained(args.output_dir)
                        print(
                            f"step {step}/{args.max_steps} - saved new best adapter "
                            f"(validation loss {validation_loss:.4f})"
                        )

                if step >= args.max_steps:
                    break

        print(f"Completed pass over train loader ({batches_per_epoch} batches).")

    training_summary = {
        "base_model": args.model,
        "max_steps": args.max_steps,
        "best_step": best_step,
        "best_validation_loss": best_validation_loss,
        "final_validation_loss": final_validation_loss,
        "max_sequence_length": args.max_sequence_length,
        "learning_rate": args.learning_rate,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "initial_adapter_path": str(args.initial_adapter_path) if args.initial_adapter_path else None,
        "load_in_4bit": args.load_in_4bit,
        "drop_overlength": args.drop_overlength,
        "tokenized_train_examples": len(train_dataset),
        "tokenized_validation_examples": len(validation_dataset),
        "peak_cuda_memory_allocated_gb": round(torch.cuda.max_memory_allocated() / (1024**3), 3),
        "peak_cuda_memory_reserved_gb": round(torch.cuda.max_memory_reserved() / (1024**3), 3),
    }
    (args.output_dir / "training_summary.json").write_text(
        json.dumps(training_summary, indent=2),
        encoding="utf-8",
    )
    print(
        f"Saved best LoRA adapter from step {best_step} to: {args.output_dir} "
        f"(validation loss {best_validation_loss:.4f})"
    )
    print(
        "Peak CUDA memory: "
        f"{training_summary['peak_cuda_memory_allocated_gb']:.3f} GB allocated, "
        f"{training_summary['peak_cuda_memory_reserved_gb']:.3f} GB reserved"
    )


if __name__ == "__main__":
    main()

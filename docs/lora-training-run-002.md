# LoRA Training Run 002

Date: 2026-07-09

## Goal

Train a second short LoRA adapter using the SFT V2 schema-guidance format.

## Why

Failure Pattern Analysis 001 showed that LoRA Run 001 mostly failed by placing
columns on the wrong table.

Run 002 tests whether adding explicit table-column ownership and join hints to
the SFT prompt helps.

## Data

Training file:

```text
data/bird_mini_dev/sft_v2/train_sft_v2.jsonl
```

Validation file:

```text
data/bird_mini_dev/sft_v2/validation_sft_v2.jsonl
```

Counts:

```text
train examples: 400
validation examples: 100
```

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py --train-path data\bird_mini_dev\sft_v2\train_sft_v2.jsonl --validation-path data\bird_mini_dev\sft_v2\validation_sft_v2.jsonl --max-sequence-length 3072 --max-steps 20 --gradient-accumulation-steps 4 --eval-every 5 --validation-limit 10 --output-dir models\tinysql-coder-lora-run-002
```

## Result

```text
step 5  validation loss: 0.3622
step 10 validation loss: 0.3434
step 15 validation loss: 0.3424
step 20 validation loss: 0.3257
```

Saved adapter:

```text
models/tinysql-coder-lora-run-002
```

## Lesson

The V2 training run completed successfully with `max_sequence_length=3072`.

Validation loss was slightly lower than Run 001:

```text
Run 001 final validation loss: 0.3360
Run 002 final validation loss: 0.3257
```

Loss improved slightly, but execution evaluation is still the real test.

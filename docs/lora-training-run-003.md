# LoRA Training Run 003

Date: 2026-07-09

## Goal

Train a third short LoRA adapter using join-focused SFT V3 data.

## Why

Run 002 added schema guidance, but still scored 0/20 execution matches.

Run 003 tests a different idea:

```text
show the model more join-heavy examples during training
```

This is called oversampling. We did not invent new labels; we duplicated
training examples whose gold SQL contains joins.

## Data

Training file:

```text
data/bird_mini_dev/sft_v3/train_sft_v3.jsonl
```

Validation file:

```text
data/bird_mini_dev/sft_v3/validation_sft_v3.jsonl
```

Counts:

```text
original train examples: 400
join train examples: 326
V3 train examples after oversampling: 726
validation examples: 100
```

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py --train-path data\bird_mini_dev\sft_v3\train_sft_v3.jsonl --validation-path data\bird_mini_dev\sft_v3\validation_sft_v3.jsonl --max-sequence-length 3072 --max-steps 20 --gradient-accumulation-steps 4 --eval-every 5 --validation-limit 10 --output-dir models\tinysql-coder-lora-run-003
```

## Result

```text
step 5  validation loss: 0.3759
step 10 validation loss: 0.3493
step 15 validation loss: 0.3377
step 20 validation loss: 0.3306
```

Saved adapter:

```text
models/tinysql-coder-lora-run-003
```

## Lesson

Validation loss was slightly worse than Run 002, but loss is not the final
metric for SQL.

Run 003 must be judged by execution accuracy.

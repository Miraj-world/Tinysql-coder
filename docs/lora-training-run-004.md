# LoRA Training Run 004

Date: 2026-07-09

## Goal

Train a fourth short LoRA adapter using hard-join-focused SFT V4 data.

## Why

Run 003 improved execution accuracy, but its successful join was simple.

Run 004 focuses more on:

```text
multi-table joins
subqueries
harder schema relationships
```

## Data

Training file:

```text
data/bird_mini_dev/sft_v4/train_sft_v4.jsonl
```

Validation file:

```text
data/bird_mini_dev/sft_v4/validation_sft_v4.jsonl
```

Counts:

```text
original train examples: 400
join train examples: 326
hard join train examples: 119
V4 train examples after oversampling: 861
```

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py --train-path data\bird_mini_dev\sft_v4\train_sft_v4.jsonl --validation-path data\bird_mini_dev\sft_v4\validation_sft_v4.jsonl --max-sequence-length 3072 --max-steps 20 --gradient-accumulation-steps 4 --eval-every 5 --validation-limit 10 --output-dir models\tinysql-coder-lora-run-004
```

## Result

```text
step 5  validation loss: 0.3720
step 10 validation loss: 0.3436
step 15 validation loss: 0.3221
step 20 validation loss: 0.3039
```

Saved adapter:

```text
models/tinysql-coder-lora-run-004
```

## Lesson

Run 004 had the best validation loss so far.

But as usual, execution evaluation is the real test.

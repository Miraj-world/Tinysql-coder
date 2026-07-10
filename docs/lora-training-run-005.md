# LoRA Training Run 005

Date: 2026-07-09

## Goal

Train a fifth short LoRA adapter using SFT V5 ownership-teacher data.

## Data

Training file:

```text
data/bird_mini_dev/sft_v5/train_sft_v5.jsonl
```

Validation file:

```text
data/bird_mini_dev/sft_v5/validation_sft_v5.jsonl
```

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py --train-path data\bird_mini_dev\sft_v5\train_sft_v5.jsonl --validation-path data\bird_mini_dev\sft_v5\validation_sft_v5.jsonl --max-sequence-length 3072 --max-steps 20 --gradient-accumulation-steps 4 --eval-every 5 --validation-limit 10 --output-dir models\tinysql-coder-lora-run-005
```

## Result

```text
step 5  validation loss: 0.5890
step 10 validation loss: 0.4423
step 15 validation loss: 0.3768
step 20 validation loss: 0.3452
```

Saved adapter:

```text
models/tinysql-coder-lora-run-005
```

## Lesson

The training run completed, but validation loss is not comparable to prior
SQL-only runs because the target now includes ownership notes plus final SQL.
Execution evaluation is the deciding metric.

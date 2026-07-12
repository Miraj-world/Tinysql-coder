# LoRA Training Run 007

Date: 2026-07-12

## Goal

Train a LoRA adapter on V6 data regenerated with cleaner schema guidance.

## Why

Run 006 learned the short V6 plan format, but the prompt still contained noisy
join hints. Run 007 tests whether cleaner join guidance helps the model choose
better source tables.

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py `
  --train-path data\bird_mini_dev\sft_v6\train_sft_v6.jsonl `
  --validation-path data\bird_mini_dev\sft_v6\validation_sft_v6.jsonl `
  --output-dir models\tinysql-coder-lora-run-007 `
  --max-steps 80 `
  --eval-every 10
```

## Data

```text
raw train examples: 738
raw validation examples: 100
tokenized train examples: 652
tokenized validation examples: 89
```

## Training

```text
device: NVIDIA GeForce RTX 4070 Laptop GPU
trainable params: 4,399,104
all params: 498,431,872
trainable percent: 0.8826
```

Validation loss:

```text
step 10: 0.3054
step 20: 0.2506
step 30: 0.2155
step 40: 0.2058
step 50: 0.1920
step 60: 0.1890
step 70: 0.1859
step 80: 0.1841
```

Run 007 reached a slightly lower validation loss than Run 006.

## Output

```text
models/tinysql-coder-lora-run-007
```

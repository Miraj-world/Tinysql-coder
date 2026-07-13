# LoRA Training Run 008

Date: 2026-07-13

## Goal

Train a LoRA adapter on SFT V7 source-table supervision.

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py `
  --train-path data\bird_mini_dev\sft_v7\train_sft_v7.jsonl `
  --validation-path data\bird_mini_dev\sft_v7\validation_sft_v7.jsonl `
  --output-dir models\tinysql-coder-lora-run-008 `
  --max-steps 80 `
  --eval-every 10
```

## Data

```text
raw train examples: 746
raw validation examples: 100
tokenized train examples: 660
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
step 10: 0.2897
step 20: 0.2474
step 30: 0.2102
step 40: 0.2042
step 50: 0.1974
step 60: 0.1930
step 70: 0.1849
step 80: 0.1733
```

Run 008 had lower validation loss than Run 007, but validation loss alone is
not the project goal. Execution evaluation decides whether the SQL is useful.

## Output

```text
models/tinysql-coder-lora-run-008
```

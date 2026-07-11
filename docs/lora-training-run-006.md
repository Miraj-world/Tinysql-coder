# LoRA Training Run 006

Date: 2026-07-11

## Goal

Train a LoRA adapter on the error-aware SFT V6 dataset.

## Why

V6 was designed after two lessons:

```text
V5 ownership reasoning was too verbose and hurt generation.
Post-generation repair helped, but could not fix wrong query plans.
```

Run 006 tests whether short plan-type supervision helps the model choose a
better SQL shape before generating the final query.

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py `
  --train-path data\bird_mini_dev\sft_v6\train_sft_v6.jsonl `
  --validation-path data\bird_mini_dev\sft_v6\validation_sft_v6.jsonl `
  --output-dir models\tinysql-coder-lora-run-006 `
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

Some examples were dropped after tokenization because the assistant answer was
fully truncated at the 2048-token sequence limit.

## Training

```text
device: NVIDIA GeForce RTX 4070 Laptop GPU
trainable params: 4,399,104
all params: 498,431,872
trainable percent: 0.8826
```

Validation loss:

```text
step 10: 0.3117
step 20: 0.2520
step 30: 0.2186
step 40: 0.2097
step 50: 0.1956
step 60: 0.1915
step 70: 0.1898
step 80: 0.1895
```

## Output

```text
models/tinysql-coder-lora-run-006
```

## Lesson

The model learned the V6 training format in the loss sense. The real question
is whether that improves execution accuracy, which is captured in the Run 006
evaluation note.

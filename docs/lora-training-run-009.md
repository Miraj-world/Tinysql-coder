# LoRA Training Run 009

Date: 2026-07-14

## Goal

Test whether Run 007 stopped too early by training the same clean V6 recipe for
160 steps instead of 80.

This is a controlled experiment. The dataset, prompt format, seed, model, LoRA
configuration, and learning rate stayed unchanged. Only the maximum number of
training steps changed.

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py `
  --train-path data\bird_mini_dev\sft_v6\train_sft_v6.jsonl `
  --validation-path data\bird_mini_dev\sft_v6\validation_sft_v6.jsonl `
  --output-dir models\tinysql-coder-lora-run-009 `
  --max-steps 160 `
  --eval-every 10
```

## Data and Model

```text
raw train examples: 738
raw validation examples: 100
tokenized train examples: 652
tokenized validation examples: 89
base model: Qwen/Qwen2.5-Coder-0.5B-Instruct
GPU: NVIDIA GeForce RTX 4070 Laptop GPU
trainable parameters: 4,399,104
all parameters: 498,431,872
```

## Validation Loss

| Step | Loss | Step | Loss |
| ---: | ---: | ---: | ---: |
| 10 | 0.3054 | 90 | 0.1724 |
| 20 | 0.2506 | 100 | 0.1694 |
| 30 | 0.2155 | 110 | 0.1917 |
| 40 | 0.2058 | 120 | 0.1730 |
| 50 | 0.1920 | 130 | 0.1768 |
| 60 | 0.1890 | 140 | 0.1734 |
| 70 | 0.1859 | 150 | 0.1744 |
| 80 | 0.1841 | 160 | 0.1631 |

Run 007 ended at step 80 with validation loss 0.1841. Run 009 finished at
0.1631. The curve fluctuated after step 100, so longer training helped overall
but was not smoothly improving at every checkpoint.

## Output

```text
models/tinysql-coder-lora-run-009
```

The adapter is a local ignored artifact. Its held-out execution result is
documented in [Eval 013](eval-013-lora-run-009.md).

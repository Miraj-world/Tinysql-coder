# LoRA Training Run 010 - Qwen 1.5B

Date: 2026-07-14

## Goal

Test whether increasing base-model capacity improves semantic text-to-SQL
accuracy after the 0.5B system plateaued at 29/100 after repair.

## Configuration

```text
base model: Qwen/Qwen2.5-Coder-1.5B-Instruct
training data: clean SFT V6
raw training rows: 738
tokenized training rows: 652
raw validation rows: 100
tokenized validation rows: 89
max sequence length: 1536
batch size: 1
gradient accumulation: 8
learning rate: 0.0001
maximum steps: 120
validation interval: 10
```

The 1536-token limit was selected after readiness testing. Training used nearly
all available memory on the 8 GB RTX 4070 Laptop GPU, so 2048 tokens would have
carried substantial out-of-memory risk.

## Model and LoRA Size

```text
total parameters:          1,552,946,688
trainable LoRA parameters: 9,232,384
trainable percentage:      0.5945%
```

## Validation Loss

| Step | Validation loss |
| ---: | ---: |
| 10 | 0.3734 |
| 20 | 0.2191 |
| 30 | 0.1708 |
| 40 | 0.1626 |
| 50 | 0.1512 |
| 60 | 0.1467 |
| 70 | 0.1485 |
| 80 | 0.1433 |
| 90 | 0.1473 |
| 100 | 0.1423 |
| 110 | 0.1365 |
| 120 | 0.1327 |

The training pipeline saved a checkpoint only when validation improved. Step
120 was both the final step and the best checkpoint.

## Resource Result

```text
peak CUDA memory allocated: 6.209 GB
adapter size:                about 37 MB
training duration:           about 28 minutes
```

The adapter and generated outputs are local ignored artifacts:

```text
models/tinysql-coder-lora-run-010
outputs/lora-run-010
```

Execution results are documented in [Eval 015](eval-015-lora-run-010.md).

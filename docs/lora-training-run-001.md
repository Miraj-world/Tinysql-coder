# LoRA Training Run 001

Date: 2026-07-09

## Goal

Run the first real LoRA fine-tuning pass after the smoke test.

The smoke test proved the training stack works. This run uses the full SFT
training file, but still keeps the step count small so we can learn safely
before spending time on longer training.

## Why

Our baseline model struggled to write correct SQL even after receiving schema
text. The next hypothesis is:

```text
The base coder model needs supervised fine-tuning on our schema-grounded
question-to-SQL examples.
```

This run trains only a small LoRA adapter instead of all Qwen weights.

## Script

```text
scripts/train_lora.py
```

## Data

Training file:

```text
data/bird_mini_dev/sft/train_sft.jsonl
```

Validation file:

```text
data/bird_mini_dev/sft/validation_sft.jsonl
```

Counts:

```text
train examples: 400
validation examples: 100
```

## Model

Base model:

```text
Qwen/Qwen2.5-Coder-0.5B-Instruct
```

LoRA adapter target:

```text
q_proj
k_proj
v_proj
o_proj
gate_proj
up_proj
down_proj
```

Trainable parameters:

```text
4,399,104
```

Total parameters:

```text
498,431,872
```

Trainable percent:

```text
0.8826%
```

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py --max-steps 20 --gradient-accumulation-steps 4 --eval-every 5 --validation-limit 10 --output-dir models\tinysql-coder-lora-run-001
```

## Result

Training completed successfully on:

```text
NVIDIA GeForce RTX 4070 Laptop GPU
```

Loss log:

```text
step 5  validation loss: 0.3615
step 10 validation loss: 0.3430
step 15 validation loss: 0.3476
step 20 validation loss: 0.3360
```

Saved adapter:

```text
models/tinysql-coder-lora-run-001
```

The `models/` folder is ignored by Git, so the adapter stays local.

## Lesson

The real LoRA training loop works.

The validation loss moved from `0.3615` to `0.3360` over this short run, which
suggests the adapter is learning something. This does not prove SQL quality yet.
Loss is only a training signal. The real test is whether the trained adapter
generates better SQL and improves execution accuracy.

## Next Step

Load the LoRA adapter during inference and run the same baseline evaluation set.

We should compare:

```text
base Qwen predictions
vs
Qwen + LoRA Run 001 predictions
```

The important metric is execution accuracy against the SQLite databases.

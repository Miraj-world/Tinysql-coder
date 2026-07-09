# LoRA Training Smoke Test

Date: 2026-07-09

## Goal

Verify that the local machine can run a tiny LoRA fine-tuning loop on the GPU.

## Why

Before running a real fine-tune, we need to prove the training stack works:

```text
CUDA
model loading
tokenization
LoRA adapter injection
loss computation
backpropagation
optimizer step
adapter saving
```

This smoke test is intentionally tiny. It is not meant to produce a useful model.

## Script

```text
scripts/train_lora_smoke_test.py
```

## Setup

Model:

```text
Qwen/Qwen2.5-Coder-0.5B-Instruct
```

Training data:

```text
data/bird_mini_dev/sft/train_sft.jsonl
```

Smoke-test settings:

```text
examples: 4
steps: 2
max_sequence_length: 2048
LoRA rank: 8
LoRA alpha: 16
learning rate: 2e-4
```

## Result

```text
device: NVIDIA GeForce RTX 4070 Laptop GPU
trainable params: 4,399,104
all params: 498,431,872
trainable percent: 0.8826
step 1/2 loss: 1.8960
step 2/2 loss: 1.7379
```

Saved local adapter:

```text
models/lora-smoke-test
```

The `models/` folder is ignored by Git, so this adapter is local only.

## Lesson

The local CUDA + LoRA training path works.

We can now move from readiness checks to a real short fine-tuning run.

## Next Step

Create a first real LoRA training script with:

```text
train examples: 400
validation examples: 100
max_sequence_length: 2048
small number of epochs or capped steps
adapter output: models/tinysql-coder-lora
```

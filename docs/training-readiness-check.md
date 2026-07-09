# Training Readiness Check

Date: 2026-07-09

## Goal

Check whether the project is ready for the first supervised fine-tuning run.

## Why

Before training, we need to confirm:

```text
1. The SFT files exist.
2. The model tokenizer can read the examples.
3. The examples fit within a reasonable sequence length.
4. The Python environment can use the GPU.
```

Starting training before checking these can waste time or crash halfway through.

## Script

```text
scripts/check_training_readiness.py
```

## Result

SFT files:

```text
train: 400 examples
validation: 100 examples
```

PyTorch / CUDA:

```text
torch version: 2.11.0+cu128
torch CUDA build: 12.8
cuda available: True
cuda device 0: NVIDIA GeForce RTX 4070 Laptop GPU
```

The machine has an NVIDIA GPU, and the Python environment can now use it through CUDA-enabled PyTorch.

## Token Lengths

Measured across all 500 SFT examples:

```text
min: 211
avg: 509.6
p95: 1068
max: 1198
```

Sequence length coverage:

```text
1024 tokens: covers 457/500 examples
2048 tokens: covers 500/500 examples
4096 tokens: covers 500/500 examples
```

## Decision

Use this as the first training sequence length:

```text
max_sequence_length = 2048
```

Why:

```text
It covers every current training and validation example.
It is smaller and cheaper than 4096.
It gives enough room for schema + question + evidence + SQL.
```

## CUDA Setup

CUDA-enabled PyTorch was installed with the PyTorch CUDA 12.8 wheel index:

```text
https://download.pytorch.org/whl/cu128
```

The install was routed through a project-local temporary directory so large wheel downloads do not depend on limited system temp space.

## Next Step

Create a small training smoke test that verifies the LoRA/SFT training loop before running a longer fine-tuning job.

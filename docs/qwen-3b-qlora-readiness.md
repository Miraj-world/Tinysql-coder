# Qwen 3B QLoRA Readiness

Date: 2026-07-14

## Why QLoRA

Runs 011 and 012 showed that better data and relationship context helped, but
the 1.5B adapter still did not pass the existing best system. The next justified
capacity step is `Qwen/Qwen2.5-Coder-3B-Instruct`.

A normal FP16 3B LoRA run is too large for the local 8 GB RTX 4070 Laptop GPU.
QLoRA keeps the base model frozen in 4-bit NF4 form and trains only small LoRA
weights.

Official references:

- <https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct>
- <https://huggingface.co/docs/transformers/quantization/bitsandbytes>

## Implementation

Both training and inference now accept:

```text
--load-in-4bit
```

The configuration uses:

```text
quantization type:     NF4
double quantization:   enabled
compute type:          float16
trainable method:      LoRA/QLoRA
bitsandbytes:          0.49.2
```

The existing FP16 path remains unchanged unless the flag is supplied.

## Verified Smoke Results

One-question 3B inference completed successfully in 4-bit mode.

Five-step QLoRA training also completed:

```text
base model:                   Qwen2.5-Coder-3B-Instruct
trainable parameters:         14,966,784
total parameters:             3,100,905,472
trainable percentage:         0.4827%
sequence length:              2,080
peak CUDA allocated:          4.679 GB
peak CUDA reserved:           6.760 GB
step 5 validation loss:       0.2300
```

This proves the 3B model can be fine-tuned locally without exceeding the 8 GB
GPU limit.

## Full-Run Memory Correction

The first 400-step Run 013 attempt used the same 2,080-token limit as the smoke
test. It reached step 37, then a longer shuffled example caused a CUDA
out-of-memory error. A five-step smoke test had not sampled enough of the data
to expose that worst case.

The corrected training path adds `--drop-overlength` and uses a 1,792-token
limit. It removes a whole example when the complete assistant answer will not
fit; it does not truncate the gold SQL and accidentally teach an incomplete
query.

```text
raw training examples:         5,825
safe training examples:        5,442
dropped training examples:       383
raw validation examples:         776
safe validation examples:        776
dropped validation examples:       0
five-step validation loss:       0.2297
peak CUDA allocated:             5.777 GB
peak CUDA reserved:              9.193 GB
automated tests:                 40 passed
```

This is a safer basis for the full run: every retained example contains its
complete SQL answer, and the validation set remains unchanged.

## Untrained 3B Baseline

The quantized base model was evaluated on the fixed 100-question set before
fine-tuning:

```text
raw execution matches:        22/100
raw SQL executed:             57/100
repaired execution matches:   27/100
repaired SQL executed:        72/100
```

The base model is more fluent than the smaller models, but it still invents
columns and unnecessary joins. Capacity alone is not enough; Run 013 will test
the 3B model with the leakage-guarded filtered BIRD training data.

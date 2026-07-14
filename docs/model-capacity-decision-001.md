# Model Capacity Decision 001 - Move to Qwen 1.5B

Date: 2026-07-14

## Decision

Run 010 will move from:

```text
Qwen/Qwen2.5-Coder-0.5B-Instruct
```

to:

```text
Qwen/Qwen2.5-Coder-1.5B-Instruct
```

## Why We Changed Direction

Nine 0.5B LoRA runs, cleaner schema guidance, longer training, and four guarded
repair experiments produced a useful research pipeline but not a dependable
text-to-SQL model.

The most reliable result is the full 100-example Run 009 benchmark:

```text
raw execution matches:           22/100
execution matches after repair:  29/100
executable SQL after repair:      75/100
```

The largest remaining failure group contains 46 queries that execute but return
the wrong rows. That is a semantic planning problem, not a syntax problem.
Additional alias and token repairs cannot safely reconstruct the intended
aggregation, filters, ranking, or multi-table plan.

The training corpus also contains only 400 unique training questions. The V6
file has 738 rows because difficult patterns are oversampled; repetition adds
emphasis but does not add new knowledge. The 0.5B model improved with longer
training, but the gain was small and uneven.

Together, these results indicate that model capacity is now a more promising
variable than another prompt-label or repair experiment.

## Run 010 Controls

Run 010 keeps the strongest known parts of the project fixed:

- clean V6 schema guidance and error-aware prompt format;
- LoRA rather than full-model fine-tuning;
- batch size 1 and gradient accumulation for the 8 GB laptop GPU;
- gradient checkpointing;
- the fixed 100-example execution benchmark;
- the guarded SQL repair stack;
- best-validation checkpoint saving.

The initial memory-safe recipe is:

```text
base model: Qwen2.5-Coder-1.5B-Instruct
max sequence length: 1536
learning rate: 0.0001
maximum steps: 120
evaluation interval: 10 steps
```

The sequence-length readiness check found:

```text
838 total train + validation examples
average length: 1070 tokens
95th percentile: 2358 tokens
1536 tokens fully covers 713/838 examples
2048 tokens fully covers 741/838 examples
```

We start at 1536 to leave GPU headroom. A one-step smoke run must succeed before
the full run begins.

## Readiness and Smoke Result

The 1.5B readiness and one-step LoRA smoke checks succeeded on the RTX 4070
Laptop GPU:

```text
tokenized training examples:    652
tokenized validation examples:  89
total model parameters:          1,552,946,688
trainable LoRA parameters:       9,232,384
step 1 training loss:            1.1781
step 1 validation loss:          0.8193
adapter save:                    successful
```

This proves the 1.5B model can be fine-tuned locally with FP16 LoRA, gradient
checkpointing, batch size 1, and a 1536-token limit. QLoRA and `bitsandbytes`
are not required for the first controlled run.

## Success Criteria

Run 010 will be measured on execution results, not training loss alone:

```text
minimum promising milestone: 50/100 after repair
longer-term usable target:    80/100 or better
```

If 1.5B improves accuracy but remains below 50/100, the next step should focus
on adding diverse, verified semantic training examples rather than repeating
the same 400 questions for more epochs.

## Outcome

Run 010 improved raw execution accuracy from 22/100 to 26/100. Its repaired
score was 28/100, but an execution-fallback cascade using repaired Run 009 as
primary and repaired Run 010 as fallback reached 35/100. The 50/100 milestone
was not met. Full results are in [Eval 015](eval-015-lora-run-010.md).

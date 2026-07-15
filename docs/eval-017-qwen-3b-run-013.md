# Eval 017: Qwen 3B QLoRA Run 013

Date: 2026-07-14

## Why This Run

The 1.5B experiments plateaued below the project goal even after data and SQL
repair improvements. Run 013 tests whether a larger 3B coding model, trained on
the database-disjoint V9 data, improves real execution accuracy.

## Training

```text
base model:                    Qwen2.5-Coder-3B-Instruct
method:                        4-bit NF4 QLoRA
safe training examples:        5,442
validation examples:             776
steps:                            400
best step:                        350
step-25 validation loss:        0.1782
best validation loss:           0.1364
peak CUDA allocated:            5.836 GB
```

The saved adapter is the step-350 state, not the slightly worse final state.

## Fixed 100-Question Results

| System | Execution matches | SQL executed |
|---|---:|---:|
| Untrained Qwen 3B | 22/100 | 57/100 |
| Untrained Qwen 3B + repair | 27/100 | 72/100 |
| Run 013 | 28/100 | 75/100 |
| Run 013 + repair | **34/100** | 90/100 |
| Previous 009/010/012 cascade | 35/100 | 96/100 |
| Run 013 primary + previous cascade fallback | **36/100** | **98/100** |

Run 013 is the strongest single repaired model so far. The execution-only
fallback rule also raises the overall project best from 35 to 36 correct.

## What We Learned

The larger model and diverse training data helped: repaired accuracy rose seven
points over the untrained 3B baseline. However, 98 predictions now execute and
only 36 return the correct rows. This means syntax and basic schema validity are
no longer the main bottleneck. Most remaining failures choose the wrong table,
condition, aggregation, relationship, or database value.

## Next Step

Add inference-time database-value retrieval without reading gold SQL. Relevant
real values can help the model ground names, codes, dates, and categorical
conditions that are difficult to infer from column names alone.

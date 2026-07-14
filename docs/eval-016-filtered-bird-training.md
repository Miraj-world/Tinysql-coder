# Eval 016 - Filtered BIRD Training, Runs 011 and 012

Date: 2026-07-14

## Question

Does replacing repeated mini-dev training examples with 6,601 curated BIRD
training pairs make the local Qwen2.5-Coder-1.5B system better?

## Run 011

Run 011 trained a fresh 1.5B LoRA adapter on V8:

```text
unique source rows:            6,601
train rows:                    5,825
validation rows:                 776
max sequence length:           2,048
optimizer steps:                 400
effective examples seen:       3,200
learning rate:                  5e-5
best step:                       400
best validation loss:         0.1567
peak CUDA allocation:          6.951 GB
```

Run 011 result:

| Variant | Execution matches | SQL executed |
|---|---:|---:|
| Run 011 direct prompt | 13/100 | 61/100 |
| Run 011 + repair | 19/100 | 79/100 |
| Run 011 + full schema guidance + repair | 24/100 | 88/100 |

The data was clean and validation improved, but the model made many incorrect
joins. Supplying verified relationships at inference helped by five points,
which showed a train/inference context mismatch.

## Run 012

Run 012 continued from Run 011 using V9 relationship-aligned prompts:

```text
initial adapter:               Run 011
max sequence length:           2,080
additional optimizer steps:      200
effective additional examples: 1,600
learning rate:                  2e-5
best step:                       200
best validation loss:         0.1555
peak CUDA allocation:          7.264 GB
```

Run 012 result:

| Variant | Execution matches | SQL executed |
|---|---:|---:|
| Run 012 raw | 20/100 | 65/100 |
| Run 012 + repair | 27/100 | 87/100 |
| Existing 009/010 cascade + Run 012 fallback | 35/100 | 96/100 |

Relationship-aligned continuation improved the new-data adapter by seven raw
points and eight repaired points over Run 011. It almost matched Run 010 after
repair, but did not establish a new best.

## Comparison With the Existing Best

| System | Execution matches | SQL executed |
|---|---:|---:|
| Run 010 raw | **26/100** | 62/100 |
| Run 010 + repair | 28/100 | 74/100 |
| Run 009 + repair | **29/100** | 75/100 |
| Run 012 raw | 20/100 | 65/100 |
| Run 012 + repair | 27/100 | 87/100 |
| Run 009 -> Run 010 cascade | **35/100** | 92/100 |
| Run 009 -> Run 010 -> Run 012 cascade | **35/100** | 96/100 |

The safe three-model cascade increases executability from 92 to 96 but does not
increase correct results. Executability is useful, but an executable wrong SQL
query is still wrong.

## What We Learned

1. More curated data is necessary but not sufficient for a 1.5B local model.
2. Training loss and unseen-database validation loss can improve while the
   target benchmark gets worse.
3. Foreign-key context matters: aligning relationship guidance recovered much
   of Run 011's loss.
4. The official recipe's stronger 3B model, value retrieval, longer context,
   and two full epochs are material differences, not minor details.
5. We must not build a selector using the 100 benchmark answers. Run 011 and
   Run 012 have complementary wins, but choosing them by question ID would be
   test-set overfitting.

## Decision

Keep Run 010 as the best raw adapter, Run 009 + repair as the best single-model
pipeline, and the Run 009 -> Run 010 cascade as the best correct-result system.

Keep the filtered-data and relationship-aligned pipeline because it is a sound,
leakage-guarded foundation for the next hardware-appropriate experiment. Do not
claim that Runs 011 or 012 produced a better model.

The next justified direction is either:

- QLoRA with a stronger 3B model and retrieved database values; or
- a separately trained selector validated outside the fixed 100-question test
  set.

Repeating more 1.5B steps on the same compact prompts is not justified by these
results.

# Eval 019: Unseen BIRD Dev Questions

Date: 2026-07-15

## Why this test was run

The earlier 100-question benchmark was repeatedly used while choosing models,
prompts, repairs, consensus rules, and the SQL judge. It remained useful for
development comparisons, but it was no longer a clean final test.

This evaluation measures the already-selected Run 013 model pipeline on
questions that were not used during project development. No training,
decoding, retrieval, or repair rule was changed after seeing these results.

## Test-set construction

The source is the official
[BIRD Dev 2025-11-06 release](https://huggingface.co/datasets/birdsql/bird_sql_dev_20251106),
which contains 1,534 questions with executable gold SQL.

The reproducible sampler is `scripts/create_unseen_bird_eval_set.py`.

- Excluded all 500 question IDs from BIRD mini-dev.
- Also excluded normalized question-text matches from mini-dev.
- Excluded normalized question-text matches from the 6,601-row filtered
  training set.
- Left 1,033 eligible questions.
- Froze 100 questions with seed `20260715` before running the model.
- Preserved the eligible pool's approximate difficulty distribution: 69
  simple, 20 moderate, and 11 challenging.
- Verified that all 100 gold queries execute on the local SQLite databases.

Generated artifacts are in `outputs/unseen-bird-dev-100/` and remain ignored by
Git because they include bulky model outputs.

## Locked configuration

- Base model: `Qwen/Qwen2.5-Coder-3B-Instruct`
- Adapter: `models/tinysql-coder-3b-qlora-run-013`
- Loading: 4-bit NF4
- Prompt: `direct_join_v9` plus the existing leakage-safe value retriever
- Decoding: greedy, one beam
- Post-processing: the existing guarded repair pipeline, unchanged

This test evaluates the strongest single-model pipeline. It does not rerun the
ten-source semantic-judge ensemble because doing so requires generating every
candidate source again and the project decision is to stop spending substantial
time on further optimization.

## Results

| Configuration | Execution matches | SQL executed | Exact SQL matches |
|---|---:|---:|---:|
| Run 013 + values, raw | 36/100 | 74/100 | 11/100 |
| Run 013 + values + guarded repair | **43/100** | **83/100** | 11/100 |

The repair pipeline changed 24 predictions. It fixed eight previously wrong
answers and regressed one previously correct answer, for a net gain of seven.

### By difficulty after repair

| Difficulty | Correct | Accuracy |
|---|---:|---:|
| Simple | 39/69 | 56.5% |
| Moderate | 2/20 | 10.0% |
| Challenging | 2/11 | 18.2% |

## Interpretation

The correct conclusion is that the project produced a partially useful, but not
reliably general text-to-SQL system.

- The unseen score of 43/100 is credible evidence that the system learned
  transferable behavior rather than only memorizing the repeatedly viewed
  mini-dev questions.
- The same single-model configuration scored 35/100 on the earlier development
  benchmark, so this result does not show an apples-to-apples generalization
  drop. The unseen set contains a much larger proportion of simple questions.
- The earlier 46/100 score belongs to the more expensive semantic-judge
  ensemble and should not be directly compared with this single-model result.
- Repair remains valuable: it raised accuracy by seven points and executability
  by nine points without any test-specific rule changes.
- Moderate and challenging questions remain the main weakness. Correct SQL is
  still not dependable enough for unsupervised production use.

## Important limitation

These are unseen questions on the same 11 database schemas used during
development. This is a valid question-generalization test, but not an
unseen-schema test. A stronger cross-database benchmark would require new
databases and would answer a different, harder question.

## Decision

Stop model experimentation here. Preserve 43/100 as the final unseen-question
score for the practical Run 013 pipeline, keep 46/100 labeled as the best
development-set ensemble score, and do not tune against this unseen set.

# Eval 001 - Baseline Without Schema

Date: 2026-07-08

## Goal

Run a base model on a fixed 20-example validation sample before fine-tuning.

The purpose of this run was to establish a starting point. Later, after fine-tuning or prompt improvements, we can compare against this baseline.

## Model

```text
Qwen/Qwen2.5-Coder-0.5B-Instruct
```

## Runtime

```text
Device: CPU
Examples: 20
```

Note: the machine has an NVIDIA GPU, but the current PyTorch install is CPU-only. That is acceptable for a small baseline run, but actual fine-tuning should use a CUDA-enabled PyTorch install.

## Dataset

Source dataset:

```text
BIRD mini-dev
```

Evaluation sample:

```text
outputs/baseline/baseline_eval_set.jsonl
```

Predictions:

```text
outputs/baseline/baseline_predictions.jsonl
```

Sample difficulty mix:

```text
challenging: 7
moderate: 7
simple: 6
```

## Result

```text
Exact match: 0/20
```

## What Failed

The model generated SQL for every prompt, but none of the generated queries exactly matched the expected SQL.

Common failure pattern:

```text
The model guessed table names and column names.
```

For example, it often wrote plausible-looking SQL using tables that were not necessarily the correct tables from the target database.

## Why It Failed

The prompt included:

```text
database ID
question
evidence
```

The prompt did not include:

```text
table names
column names
foreign keys
schema relationships
column meanings
```

For text-to-SQL, this is a major missing piece. A model cannot reliably generate correct SQL if it does not know the database schema.

## Metric Limitation

Exact string match is strict.

Two SQL queries can sometimes be logically equivalent while using different formatting, aliases, or expression order. So `0/20 exact match` does not automatically mean every answer is completely useless.

However, the failures are still meaningful because many predictions appear schema-incorrect, not just formatting-different.

## Lesson

Text-to-SQL is not only a language-generation problem. It is also a schema-grounding problem.

The model needs database structure in the prompt or training example. Without schema context, it is forced to guess.

## Decision

Before fine-tuning, improve the data format.

The next version of the training examples and baseline prompts should include schema context.

## Next Step

Add database schema context to each example.

Target prompt shape:

```text
Instruction:
Convert the database question into a valid SQL query.

Database ID:
...

Schema:
table_1(column_a, column_b, ...)
table_2(column_c, column_d, ...)

Question:
...

Evidence:
...

Return only the SQL query.
```

After that:

```text
1. Regenerate training_data.jsonl.
2. Regenerate train.jsonl and validation.jsonl.
3. Regenerate the baseline eval set.
4. Rerun the base model baseline.
5. Compare the new result against 0/20 exact match.
```

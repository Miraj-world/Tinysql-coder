# SFT V3 Join Focus

Date: 2026-07-09

## Goal

Create a Run 003 training dataset that focuses more strongly on join-heavy SQL.

## Why

Run 002 added schema guidance, but execution accuracy did not improve.

Failure analysis still showed:

```text
wrong_table_for_column: 11
```

The training data itself is mostly join-heavy:

```text
train examples: 400
join examples: 326
validation examples: 100
validation join examples: 81
```

So Run 003 should make join behavior even more visible during training.

## Script

```text
scripts/prepare_sft_data_v3.py
```

## Method

SFT V3 starts from SFT V2, keeps the same schema-guidance prompt, and duplicates
join examples in the training set.

This is oversampling, not synthetic data generation.

Plain English:

```text
Show the model more examples of the thing it is currently bad at.
```

## Expected Output

```text
data/bird_mini_dev/sft_v3/train_sft_v3.jsonl
data/bird_mini_dev/sft_v3/validation_sft_v3.jsonl
```

## Mentor Note

This is a controlled experiment. If Run 003 improves wrong-table-column errors,
oversampling helped. If not, we probably need new teacher-generated examples or
a planning-style target instead of only repeating existing examples.

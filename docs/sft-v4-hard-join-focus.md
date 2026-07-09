# SFT V4 Hard Join Focus

Date: 2026-07-09

## Goal

Create a Run 004 training dataset focused on harder join patterns.

## Why

Run 003 improved to:

```text
Execution matches: 2/20
Predicted SQL executed: 4/20
```

But its successful join example was simple. The next target is:

```text
multi-table joins
subqueries
moderate/challenging join logic
```

## Script

```text
scripts/prepare_sft_data_v4.py
```

## Training Data Counts

Measured from the processed train split:

```text
train examples: 400
join examples: 326
multi-join examples: 78
subquery examples: 52
hard join examples: 119
```

Hard join means:

```text
two or more JOIN clauses
or
a subquery
```

## Method

SFT V4 starts from SFT V2 schema-guidance data and oversamples:

```text
regular join examples: 2 copies total
hard join examples: 3 copies total
non-join examples: 1 copy
```

This keeps all original examples but changes the training distribution toward
the patterns Run 003 still struggles with.

## Mentor Note

This is still not synthetic teacher data.

We are squeezing more signal out of the existing gold examples before deciding
whether we need a bigger teacher model to generate additional join-focused
training examples.

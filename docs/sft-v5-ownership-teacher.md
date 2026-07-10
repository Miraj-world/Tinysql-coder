# SFT V5 Ownership Teacher

Date: 2026-07-09

## Goal

Create a Run 005 dataset that directly teaches:

```text
needed columns -> owning tables -> join path -> final SQL
```

## Why

Run 004 was the best run so far, but failure analysis still showed:

```text
wrong_table_for_column: 12
```

The model often knew a real column name but attached it to the wrong table.

## Script

```text
scripts/prepare_sft_data_v5.py
```

## Method

SFT V5 uses the processed train and validation splits, schema guidance, and gold
SQL to build assistant targets with this shape:

```text
COLUMN_OWNERSHIP:
- column -> table
JOIN_PATH:
- table.column = table.column
FINAL_SQL:
SELECT ...
```

The model runner now extracts text after `FINAL_SQL:` before execution scoring.

## Data Counts

```text
train examples: 400
validation examples: 100
train join examples: 326
train subquery examples: 52
```

## Mentor Note

This is a deliberate experiment, not a guaranteed improvement. It teaches an
intermediate reasoning format, which may help schema grounding, but it also
increases the chance that the model emits non-SQL text during evaluation.

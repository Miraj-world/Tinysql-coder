# SFT V7 Source-Table Supervision

Date: 2026-07-13

## Goal

Create a V7 dataset that keeps the cleaner schema guidance from Run 007 and
adds gold-query-derived source-table labels.

## Why

Run 007 showed that cleaner join hints helped. The remaining bottleneck was
still table choice: the model often selected the wrong source table before it
started writing the rest of the SQL.

V7 tests whether explicit table labels help:

```text
REQUIRED_SOURCE_TABLES
PRIMARY_FACT_TABLE
```

## Script

```text
scripts/prepare_sft_data_v7.py
```

## Format

The assistant target has this shape:

```text
PLAN_TYPE: fact_table_first
REQUIRED_SOURCE_TABLES: League, Match, Team
PRIMARY_FACT_TABLE: Match
SPECIAL_OPERATIONS: aggregation, grouping, ranking_or_extreme_value
FINAL_SQL:
SELECT ...
```

## Data Counts

```text
train examples after oversampling: 746
validation examples: 100

train plan types:
fact_table_first: 220
fresh_query_plan: 354
local_schema_fix: 64
lookup_or_value_fix: 108

validation plan types:
fact_table_first: 25
fresh_query_plan: 24
local_schema_fix: 22
lookup_or_value_fix: 29
```

## Eval Prompt

`scripts/create_baseline_eval_set.py` now supports:

```powershell
.\.venv312\Scripts\python.exe scripts\create_baseline_eval_set.py `
  --prompt-style source_table_v7 `
  --output-path outputs\lora-run-008\eval_set.jsonl
```

## Runner Fix

`scripts/run_baseline_model.py` now strips leaked planning lines before the
first `SELECT` or `WITH`. This matters because V7 sometimes emits labels even
when it does not emit `FINAL_SQL:`.

## Lesson

This dataset is intentionally experimental. The labels are gold-query-derived,
but adding more labels can still make a small model over-focus on format.
Run 008 evaluates whether the extra labels help actual execution accuracy.

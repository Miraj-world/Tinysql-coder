# SFT V6 Error-Aware Planning

Date: 2026-07-10

## Goal

Create a Run 006 dataset that teaches the model to choose the right level of
SQL plan before writing the final query.

## Why

Run 005 showed that verbose ownership reasoning hurt this small model. The SQL
repair experiments then showed a more precise lesson:

```text
Some mistakes are local alias/column mistakes.
Some mistakes are lookup/value mistakes.
Some mistakes mean the model chose the wrong fact table.
Some mistakes mean the whole query shape needs to be rebuilt.
```

V6 teaches that distinction directly, but with much shorter supervision than
V5.

## Script

```text
scripts/prepare_sft_data_v6.py
```

## Format

The assistant target has this shape:

```text
PLAN_TYPE: fresh_query_plan
SOURCE_TABLES: races, results, drivers
FACT_TABLES: results, races
SPECIAL_OPERATIONS: aggregation, ranking_or_extreme_value
FINAL_SQL:
SELECT ...
```

The model runner already extracts text after `FINAL_SQL:`, so this format can
still be evaluated as executable SQL.

## Plan Types

```text
local_schema_fix
lookup_or_value_fix
fact_table_first
fresh_query_plan
```

These labels are deliberately small. The goal is not to make the model write a
long explanation. The goal is to nudge it into choosing the correct query shape.

## Data Counts

```text
train examples after oversampling: 738
validation examples: 100

train plan types:
fact_table_first: 204
fresh_query_plan: 354
local_schema_fix: 66
lookup_or_value_fix: 114

validation plan types:
fact_table_first: 24
fresh_query_plan: 24
local_schema_fix: 22
lookup_or_value_fix: 30
```

V6 oversamples:

```text
fresh_query_plan: 3x
fact_table_first: 2x
other examples: 1x
```

## Eval Prompt

`scripts/create_baseline_eval_set.py` now supports:

```powershell
.\.venv312\Scripts\python.exe scripts\create_baseline_eval_set.py `
  --prompt-style error_aware_v6 `
  --output-path outputs\lora-run-006\eval_set.jsonl
```

Generated local eval set:

```text
outputs/lora-run-006/eval_set.jsonl
```

## Validation

The generated files were checked for:

```text
train_sft_v6.jsonl: 738 rows
validation_sft_v6.jsonl: 100 rows
missing FINAL_SQL markers: 0
eval prompt style: error_aware_v6
```

## Next Step

Train LoRA Run 006 on V6:

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py `
  --train-path data\bird_mini_dev\sft_v6\train_sft_v6.jsonl `
  --validation-path data\bird_mini_dev\sft_v6\validation_sft_v6.jsonl `
  --output-dir models\tinysql-coder-lora-run-006 `
  --max-steps 80 `
  --eval-every 10
```

Then evaluate it against `outputs/lora-run-006/eval_set.jsonl`.

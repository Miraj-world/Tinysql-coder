# Eval 005 - LoRA Run 001

Date: 2026-07-09

## Goal

Evaluate the first trained LoRA adapter against the same 20-example baseline
evaluation set.

## Why

Training loss alone does not prove the model became better at SQL.

The real question is:

```text
Does Qwen + LoRA Run 001 generate SQL that executes correctly?
```

## Model

Base model:

```text
Qwen/Qwen2.5-Coder-0.5B-Instruct
```

LoRA adapter:

```text
models/tinysql-coder-lora-run-001
```

## Commands

Generate predictions:

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py --adapter-path models\tinysql-coder-lora-run-001 --output-path outputs\lora-run-001\predictions.jsonl
```

Evaluate execution:

```powershell
.\.venv312\Scripts\python.exe scripts\evaluate_sql_execution.py --predictions-path outputs\lora-run-001\predictions.jsonl --output-path outputs\lora-run-001\execution_eval.jsonl --summary-path outputs\lora-run-001\execution_eval_summary.json
```

## Result

```text
Total examples: 20
Exact matches: 0/20
Execution matches: 0/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 2/20
```

## Comparison

```text
Eval 004 base model execution matches: 1/20
Eval 005 LoRA Run 001 execution matches: 0/20

Eval 004 base model predicted SQL executed: 2/20
Eval 005 LoRA Run 001 predicted SQL executed: 2/20
```

This first LoRA run did not improve execution accuracy.

## What Failed

The model still made schema ownership mistakes.

Example:

```text
question_id: 415
db_id: card_games
```

Gold SQL uses `legalities.format` and `legalities.status`.

The model predicted:

```sql
SELECT CAST(SUM(CASE WHEN T1.hasContentWarning = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.id)
FROM cards AS T1
WHERE T1.format = 'commander' AND T1.Status = 'legal'
```

SQLite error:

```text
no such column: T1.format
```

The model understood part of the question, but placed the column on the wrong
table.

## Lesson

The training loop works, but this short 20-step LoRA run is not enough to fix
schema grounding.

The model needs stronger learning around:

```text
1. Which table owns each column.
2. Which shared keys connect tables.
3. When a join is required.
4. How to avoid inventing columns on plausible-looking tables.
```

## Next Step

Improve the fine-tuning setup before doing a longer run.

The most useful next improvement is to add a small before/after generation
script so we can inspect LoRA outputs quickly after each training run.

After that, run a longer training experiment and compare execution accuracy
again.

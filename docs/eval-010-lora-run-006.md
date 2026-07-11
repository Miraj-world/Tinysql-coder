# Eval 010 - LoRA Run 006

Date: 2026-07-11

## Goal

Evaluate LoRA Run 006 on the fixed 20-example SQL evaluation set using the V6
error-aware prompt style.

## Commands

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py `
  --adapter-path models\tinysql-coder-lora-run-006 `
  --eval-set-path outputs\lora-run-006\eval_set.jsonl `
  --output-path outputs\lora-run-006\predictions.jsonl
```

```powershell
.\.venv312\Scripts\python.exe scripts\evaluate_sql_execution.py `
  --predictions-path outputs\lora-run-006\predictions.jsonl `
  --output-path outputs\lora-run-006\execution_eval.jsonl `
  --summary-path outputs\lora-run-006\execution_eval_summary.json
```

## Result

```text
LoRA Run 006 exact matches:      2/20
LoRA Run 006 execution matches:  3/20
LoRA Run 006 predicted SQL runs: 7/20
Gold SQL runs:                   20/20
```

Run 006 matched the raw Run 004 execution score, but did not beat it.

## Comparison With Run 004

```text
Run 004 execution matches: 3/20
Run 006 execution matches: 3/20
```

Question-level change:

```text
new Run 006 match:  Q733
lost Run 004 match: Q791
shared matches:     Q555, Q1394
```

Run 006 improved the superhero lookup-style case, but regressed a simple
superhero average-height query.

## Failure Pattern

```text
wrong_table_for_column: 6
executes_wrong_result: 4
execution_match: 3
invented_column: 3
execution_error_other: 2
ambiguous_or_unqualified_column: 2
```

The main failure pattern did not change enough. The model still often chooses
the wrong source table or produces a query that runs but returns the wrong
rows.

## Repair Check

The existing repair stack was also applied to Run 006:

```powershell
.\.venv312\Scripts\python.exe scripts\repair_sql_predictions.py `
  --input-path outputs\lora-run-006\predictions.jsonl `
  --output-path outputs\lora-run-006-repaired\predictions.jsonl
```

Repaired result:

```text
Run 006 + repair execution matches:  3/20
Run 006 + repair predicted SQL runs: 10/20
```

The repair pass made more SQL executable, but did not improve execution
matches.

## Lesson

V6 was a useful negative result. Short plan labels are less harmful than V5's
verbose reasoning, but they do not solve the deeper schema and query-planning
problem.

The next likely bottleneck is schema guidance quality. The prompt's possible
join keys are too noisy because they include many same-name column matches that
are not reliable relationships. The next project step should make schema
guidance prefer real SQLite foreign keys and only use inferred same-name joins
when they are clearly safe.

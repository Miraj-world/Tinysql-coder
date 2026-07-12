# Eval 011 - LoRA Run 007

Date: 2026-07-12

## Goal

Evaluate LoRA Run 007, trained on V6 data regenerated with cleaner schema
guidance.

## Commands

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py `
  --adapter-path models\tinysql-coder-lora-run-007 `
  --eval-set-path outputs\lora-run-007\eval_set.jsonl `
  --output-path outputs\lora-run-007\predictions.jsonl
```

```powershell
.\.venv312\Scripts\python.exe scripts\evaluate_sql_execution.py `
  --predictions-path outputs\lora-run-007\predictions.jsonl `
  --output-path outputs\lora-run-007\execution_eval.jsonl `
  --summary-path outputs\lora-run-007\execution_eval_summary.json
```

## Result

```text
LoRA Run 007 exact matches:      1/20
LoRA Run 007 execution matches:  4/20
LoRA Run 007 predicted SQL runs: 6/20
Gold SQL runs:                   20/20
```

Run 007 improved raw execution accuracy over Runs 004 and 006:

```text
Run 004 execution matches: 3/20
Run 006 execution matches: 3/20
Run 007 execution matches: 4/20
```

New raw match compared with Run 006:

```text
Q1526
```

No raw Run 006 execution matches were lost.

## Repair Check

The existing repair stack was applied to Run 007:

```powershell
.\.venv312\Scripts\python.exe scripts\repair_sql_predictions.py `
  --input-path outputs\lora-run-007\predictions.jsonl `
  --output-path outputs\lora-run-007-repaired\predictions.jsonl
```

Repaired result:

```text
Run 007 + repair execution matches:  6/20
Run 007 + repair predicted SQL runs: 11/20
```

This is better than Run 006 + repair:

```text
Run 006 + repair execution matches: 3/20
Run 007 + repair execution matches: 6/20
```

But it is still slightly below the best repaired Run 004 result:

```text
Run 004 + repair execution matches: 7/20
```

## Failure Pattern

Raw Run 007:

```text
wrong_table_for_column: 7
execution_match: 4
invented_column: 3
execution_error_other: 2
ambiguous_or_unqualified_column: 2
executes_wrong_result: 2
```

Run 007 + repair:

```text
execution_match: 6
executes_wrong_result: 5
invented_column: 3
execution_error_other: 2
wrong_table_for_column: 2
ambiguous_or_unqualified_column: 2
```

## Lesson

Cleaner schema guidance helped. It improved raw model accuracy and made the
output more repairable.

The best system is still Run 004 plus repair, but Run 007 shows the right
direction: schema guidance quality matters more than adding more free-form
reasoning text.

## Next Step

Create a schema-guidance V3 / SFT V7 experiment that keeps the cleaner join
hints and adds a small number of gold-query-derived source-table labels. The
model still needs help choosing the correct fact table before it writes SQL.

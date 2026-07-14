# Eval 012 - LoRA Run 008

Date: 2026-07-13

## Goal

Evaluate LoRA Run 008, trained on V7 source-table supervision.

## Commands

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py `
  --adapter-path models\tinysql-coder-lora-run-008 `
  --eval-set-path outputs\lora-run-008\eval_set.jsonl `
  --output-path outputs\lora-run-008\predictions.jsonl
```

```powershell
.\.venv312\Scripts\python.exe scripts\evaluate_sql_execution.py `
  --predictions-path outputs\lora-run-008\predictions.jsonl `
  --output-path outputs\lora-run-008\execution_eval.jsonl `
  --summary-path outputs\lora-run-008\execution_eval_summary.json
```

## Result

```text
LoRA Run 008 exact matches:      0/20
LoRA Run 008 execution matches:  2/20
LoRA Run 008 predicted SQL runs: 5/20
Gold SQL runs:                   20/20
```

Run 008 regressed compared with Run 007:

```text
Run 007 execution matches: 4/20
Run 008 execution matches: 2/20
```

Run 008 kept:

```text
Q555
Q1394
```

But lost the Run 007 wins:

```text
Q1526
Q733
```

## Repair Check

The existing repair stack was applied to Run 008:

```powershell
.\.venv312\Scripts\python.exe scripts\repair_sql_predictions.py `
  --input-path outputs\lora-run-008\predictions.jsonl `
  --output-path outputs\lora-run-008-repaired\predictions.jsonl
```

Repaired result:

```text
Run 008 + repair execution matches:  3/20
Run 008 + repair predicted SQL runs: 8/20
```

This is worse than Run 007 + repair:

```text
Run 007 + repair execution matches: 6/20
Run 008 + repair execution matches: 3/20
```

## Failure Pattern

Raw Run 008:

```text
wrong_table_for_column: 7
ambiguous_or_unqualified_column: 4
executes_wrong_result: 3
execution_error_other: 2
execution_match: 2
hallucinated_table: 1
invented_column: 1
```

Run 008 + repair:

```text
executes_wrong_result: 5
wrong_table_for_column: 4
ambiguous_or_unqualified_column: 4
execution_match: 3
execution_error_other: 2
hallucinated_table: 1
invented_column: 1
```

## Lesson

V7 was a useful negative result.

The model learned the source-table label format well enough to lower validation
loss, but execution accuracy got worse. The extra labels likely competed with
the SQL generation objective for this small model.

The best raw LoRA run remains Run 007 at 4/20. The best overall system remains
Run 004 plus repair at 7/20.

## Next Step

Do not add more pre-SQL labels. The next useful step should be smaller and
more mechanical:

```text
improve post-generation repair for obvious syntax/alias issues, or
build a focused error-set evaluation around the remaining wrong-table cases
```

## Follow-up

These recommendations were completed in the later guarded repair experiments.
The project then returned to the cleaner V6 recipe and trained Run 009 for 160
steps. The current full-validation result is 22/100 raw and 29/100 after repair;
see [Eval 014](eval-014-lora-run-009-full-validation.md).

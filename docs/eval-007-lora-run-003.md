# Eval 007 - LoRA Run 003

Date: 2026-07-09

## Goal

Evaluate LoRA Run 003 against the same 20-example baseline evaluation set.

## Why

Run 003 used join-focused SFT V3 data. This evaluation checks whether
oversampling join-heavy examples improved SQL execution.

## Commands

Generate predictions:

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py --adapter-path models\tinysql-coder-lora-run-003 --output-path outputs\lora-run-003\predictions.jsonl
```

Evaluate execution:

```powershell
.\.venv312\Scripts\python.exe scripts\evaluate_sql_execution.py --predictions-path outputs\lora-run-003\predictions.jsonl --output-path outputs\lora-run-003\execution_eval.jsonl --summary-path outputs\lora-run-003\execution_eval_summary.json
```

## Result

```text
Total examples: 20
Exact matches: 0/20
Execution matches: 2/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 4/20
```

## Comparison

```text
Base Qwen execution matches: 1/20
LoRA Run 001 execution matches: 0/20
LoRA Run 002 execution matches: 0/20
LoRA Run 003 execution matches: 2/20
```

Run 003 is the first LoRA run to beat the base model on execution accuracy.

## Lesson

Join-focused oversampling helped.

The improvement is still small, but it is the first evidence that changing the
training distribution can improve real SQL execution.

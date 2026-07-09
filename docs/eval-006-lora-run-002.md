# Eval 006 - LoRA Run 002

Date: 2026-07-09

## Goal

Evaluate LoRA Run 002 against the same 20-example baseline evaluation set.

## Why

Run 002 trained on SFT V2, which includes explicit schema guidance:

```text
Column ownership
Possible join keys
```

This evaluation checks whether that improved generated SQL execution accuracy.

## Commands

Generate predictions:

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py --adapter-path models\tinysql-coder-lora-run-002 --output-path outputs\lora-run-002\predictions.jsonl
```

Evaluate execution:

```powershell
.\.venv312\Scripts\python.exe scripts\evaluate_sql_execution.py --predictions-path outputs\lora-run-002\predictions.jsonl --output-path outputs\lora-run-002\execution_eval.jsonl --summary-path outputs\lora-run-002\execution_eval_summary.json
```

## Result

```text
Total examples: 20
Exact matches: 0/20
Execution matches: 0/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 1/20
```

## Comparison

```text
Base Qwen execution matches: 1/20
LoRA Run 001 execution matches: 0/20
LoRA Run 002 execution matches: 0/20
```

Run 002 did not improve execution accuracy.

## Lesson

Adding schema guidance helped the training objective slightly, but did not yet
translate into correct SQL execution.

This tells us the model may need a stronger training signal than just putting
more schema guidance in the prompt.

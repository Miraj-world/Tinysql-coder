# Eval Comparison Tool

Date: 2026-07-09

## Goal

Add a repeatable way to compare two execution-evaluation runs side by side.

## Why

Raw JSONL files are useful for scripts, but hard for humans to read.

After LoRA Run 001, we needed to answer:

```text
Did the trained adapter improve, regress, or fail differently than the base model?
```

This tool creates a markdown report with:

```text
summary metrics
per-question status
base predicted SQL
LoRA predicted SQL
gold SQL
execution errors
```

## Script

```text
scripts/compare_eval_runs.py
```

## Default Command

```powershell
.\.venv312\Scripts\python.exe scripts\compare_eval_runs.py
```

By default it compares:

```text
outputs/baseline/execution_eval.jsonl
outputs/lora-run-001/execution_eval.jsonl
```

and writes:

```text
outputs/comparisons/base-vs-lora-run-001.md
```

The `outputs/` folder is ignored by Git, so comparison reports stay local.

## Lesson

This gives us a faster learning loop.

Instead of only asking:

```text
What was the score?
```

we can inspect:

```text
What kind of mistake changed?
```

That matters because SQL quality improves through failure patterns, not just
through a single accuracy number.

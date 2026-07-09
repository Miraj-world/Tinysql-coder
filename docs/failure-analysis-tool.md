# Failure Analysis Tool

Date: 2026-07-09

## Goal

Add a reusable tool for classifying SQL evaluation failures.

## Script

```text
scripts/analyze_failure_patterns.py
```

## What It Does

The script reads an execution-evaluation JSONL file and compares failed SQL
against the real SQLite schema.

It classifies failures into categories such as:

```text
wrong_table_for_column
ambiguous_or_unqualified_column
invented_column
hallucinated_table
executes_wrong_result
execution_error_other
```

## Why This Matters

Accuracy tells us whether the model won.

Failure analysis tells us what to change next.

For this project, the first analysis showed that the biggest issue is not only
hallucination. The model often chooses real column names but assigns them to the
wrong table.

That points the next experiment toward schema-grounding and join supervision.

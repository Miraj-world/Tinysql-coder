# SQL Repair Experiment 001

Date: 2026-07-09

## Goal

Try a conservative post-generation repair pass on LoRA Run 004 predictions.

## Why

Run 004 is still the best checkpoint, but most failures are schema-grounding
errors. Before training another adapter, test whether a deterministic schema
guardrail can rescue simple alias/column ownership mistakes.

## Script

```text
scripts/repair_sql_predictions.py
```

## Method

The repair pass only handles this narrow case:

```text
wrong_alias.column -> correct_alias.column
```

It only applies the repair when the correct owning table is already present in
the predicted SQL. It does not invent new joins.

## Result

```text
Raw Run 004 execution matches:      3/20
Repaired Run 004 execution matches: 3/20

Raw Run 004 predicted SQL executes:      5/20
Repaired Run 004 predicted SQL executes: 8/20
```

Failure pattern after repair:

```text
wrong_table_for_column: 9
executes_wrong_result: 5
invented_column: 3
execution_match: 3
```

## Lesson

Alias repair improves executability, but not answer correctness. This means the
next repair layer needs to understand missing or wrong joins, not just move
columns between aliases that already exist.

## Next Step

Build a join-aware repair experiment that can handle cases like:

```text
column exists on a table that is not joined yet
predicted join uses the wrong table with a similar column
literal comparison should go through a lookup table
```

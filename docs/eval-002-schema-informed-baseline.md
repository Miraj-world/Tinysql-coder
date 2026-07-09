# Eval 002 - Baseline With Schema

Date: 2026-07-08

## Goal

Rerun the baseline after adding compact database schema text to each prompt.

## Change

The model prompt now includes:

```text
Database ID
Schema
Question
Evidence
```

instead of only:

```text
Database ID
Question
Evidence
```

## Result

```text
Model: Qwen/Qwen2.5-Coder-0.5B-Instruct
Examples: 20
Exact match: 0/20
```

## What Improved

The model started using more real table and column names from the schema. For example, in the toxicology question it used `atom` and `element`, which were missing from the earlier schema-free baseline.

## What Still Failed

The generated SQL is still often logically wrong. In the toxicology example, the model used `label` as if it lived in the `atom` table, but the schema shows `label` belongs to the `molecule` table.

That means the model still needs to learn table relationships and SQL join structure, not just table and column names.

## Lesson

Adding schema helps reduce blind guessing, but schema text alone is not enough. The model also needs examples that teach how to connect tables correctly.

## Next Step

Move from exact-string checking to execution-based evaluation. We should run generated SQL and gold SQL against the same SQLite database and compare the returned results.

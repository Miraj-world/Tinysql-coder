# Eval 003 - Execution-Based Evaluation

Date: 2026-07-08

## Goal

Evaluate model SQL by running it against the real SQLite databases.

This is better than exact string match because two SQL queries can look different but return the same answer.

## Method

For each baseline prediction:

```text
1. Find the matching SQLite database using db_id.
2. Run the gold SQL.
3. Run the model-generated SQL.
4. Compare returned rows.
```

## Script

```text
scripts/evaluate_sql_execution.py
```

## Input

```text
outputs/baseline/baseline_predictions.jsonl
```

## Outputs

```text
outputs/baseline/execution_eval.jsonl
outputs/baseline/execution_eval_summary.json
```

## Result

```text
Total examples: 20
Exact matches: 0/20
Execution matches: 0/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 1/20
```

## What This Teaches Us

The low exact-match score was not just a formatting problem.

Most model-generated SQL does not even execute successfully. That means the model is still making structural SQL mistakes.

Common errors:

```text
no such column: label
no such table: card_games
no such column: name
no such column: DisplayName
```

## Diagnosis

The model improved after seeing schema text, but it still does not reliably understand how to use that schema.

The biggest remaining problems are:

```text
1. It puts columns in the wrong table.
2. It uses database names as table names.
3. It skips necessary joins.
4. It guesses column names from the English question instead of grounding them in schema.
```

## Lesson

Schema text helps, but the model also needs to learn schema reasoning:

```text
Which table contains the needed column?
Which tables must be joined?
Which key connects the tables?
```

## Next Step

Improve the prompt format so the model pays more attention to schema grounding.

Then rerun:

```text
1. baseline prediction
2. execution evaluation
```

If prompt improvements are still weak, then fine-tuning becomes more justified.

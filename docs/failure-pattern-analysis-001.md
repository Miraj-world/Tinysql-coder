# Failure Pattern Analysis 001

Date: 2026-07-09

## Goal

Analyze why LoRA Run 001 failed instead of only recording the score.

## Why

Eval 005 showed:

```text
Execution matches: 0/20
Predicted SQL executed successfully: 2/20
```

That tells us the model is not good enough yet, but it does not tell us what
to fix. We need failure categories.

## Script

```text
scripts/analyze_failure_patterns.py
```

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\analyze_failure_patterns.py
```

Default input:

```text
outputs/lora-run-001/execution_eval.jsonl
```

Default local report:

```text
outputs/analysis/lora-run-001-failure-analysis.md
```

The report stays local because `outputs/` is ignored by Git.

## Result

```text
wrong_table_for_column: 13
ambiguous_or_unqualified_column: 2
executes_wrong_result: 2
hallucinated_table: 2
execution_error_other: 1
```

## Main Finding

The dominant problem is:

```text
wrong_table_for_column
```

That means the model often knows a column name is relevant, but attaches it to
the wrong table.

Example:

```text
question_id: 415
db_id: card_games
```

The model used:

```sql
T1.format
```

where `T1` was `cards`.

But `format` belongs to:

```text
legalities(format)
```

So the correct SQL needs a join from `cards` to `legalities`.

## How We Figured This Out

We did not guess this from the final score.

First, execution evaluation gave us the concrete database error:

```text
no such column: T1.format
```

Then we looked at the predicted SQL:

```sql
FROM cards AS T1
WHERE T1.format = 'commander'
```

That tells us the model believed `format` belonged to the `cards` table.

Then we checked the real SQLite schema:

```text
cards(..., uuid, hasContentWarning, ...)
legalities(id, format, status, uuid)
```

So `format` is not fake. It is a real useful column, but it belongs to
`legalities`, not `cards`.

Finally, we repeated that check across all failed predictions with
`scripts/analyze_failure_patterns.py`. The count was:

```text
wrong_table_for_column: 13/20
```

That is why the diagnosis is:

```text
The model often knows the relevant column, but not the correct table ownership
or join path.
```

## Lesson

The next training improvement should not be random longer training.

The model needs clearer supervision for:

```text
1. Table-column ownership.
2. Join path selection.
3. Avoiding plausible but invalid table aliases.
```

## Next Step

Create a stronger SFT format for Run 002.

One useful addition would be an explicit schema map section:

```text
Column ownership:
cards: id, uuid, hasContentWarning, ...
legalities: format, status, uuid

Join hints:
cards.uuid = legalities.uuid
```

Then regenerate SFT data and run a second LoRA experiment.

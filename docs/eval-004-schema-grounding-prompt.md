# Eval 004 - Schema-Grounding Prompt Rules

Date: 2026-07-08

## Goal

Test whether explicit schema-grounding rules improve the base model before fine-tuning.

## Why

Eval 003 showed that most generated SQL did not execute. The model saw the schema, but still used columns in the wrong tables or skipped necessary joins.

This experiment asks: can clearer instructions make the base model use the schema more carefully?

## Change

The baseline prompt now includes these rules:

```text
Before writing SQL:
1. Use only tables and columns listed in the schema.
2. Do not use the database ID as a table name.
3. If the question needs columns from multiple tables, join the tables using shared key columns.
4. If a column is not in a table, do not reference it from that table.
```

## Result

```text
Total examples: 20
Exact matches: 0/20
Execution matches: 1/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 2/20
```

## Comparison Against Eval 003

```text
Eval 003 execution matches: 0/20
Eval 004 execution matches: 1/20

Eval 003 predicted SQL executed: 1/20
Eval 004 predicted SQL executed: 2/20
```

This is a small improvement, but it is still weak.

## What Improved

The model generated more joins after seeing explicit schema-grounding rules.

One query matched by execution:

```text
question_id: 1057
db_id: european_football_2
difficulty: moderate
```

Generated SQL:

```sql
SELECT AVG(home_team_goal)
FROM Country AS T1
INNER JOIN League AS T2 ON T1.id = T2.country_id
INNER JOIN Match AS T3 ON T2.id = T3.league_id
WHERE T1.name = 'Poland'
  AND T3.season = '2010/2011';
```

Even though this SQL was not an exact text match, it returned the same result as the gold SQL.

## What Still Failed

Most predictions still failed execution.

Example errors:

```text
no such column: label
no such column: T1.format
no such column: T1.DisplayName
```

These errors show that the model is still not reliably grounding each column to the correct table.

## Lesson

Prompt rules help a little, but this small base model still needs stronger learning.

The model needs to learn:

```text
1. Which table owns each column.
2. Which shared columns can connect tables.
3. When a join is required.
4. How to avoid inventing schema elements.
```

## Next Step

Create a stronger training format that teaches schema grounding directly.

One possible next format:

```text
Instruction
Schema
Question
Evidence
SQL
```

Then fine-tune the small model on the official gold examples.

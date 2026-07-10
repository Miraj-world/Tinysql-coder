# SQL Repair Experiment 003

Date: 2026-07-09

## Goal

Extend Run 004 repair with a semantic lookup-table repair.

## Why

After join-aware repair, some predictions executed successfully but still
returned the wrong answer. One important pattern was:

```text
ID column = human-readable label
```

Example:

```sql
T1.eye_colour_id = 'Gold'
```

That SQL runs, but it is semantically wrong. `eye_colour_id` stores a foreign
key, while `Gold` belongs in the lookup table `colour`.

## Script

```text
scripts/repair_sql_predictions.py
```

## Method

The repair pass now has three layers:

```text
1. Alias repair
2. Join repair
3. Lookup repair
```

Lookup repair only applies when:

```text
- the SQL already executes
- a qualified column is compared to a string literal
- that column is a foreign key
- the referenced table has exactly one text column containing that literal
- the repaired SQL still executes
```

This keeps the repair conservative. It does not use the gold SQL during repair.

## Result

```text
Raw Run 004 execution matches:                 3/20
Run 004 + alias repair execution matches:     3/20
Run 004 + join repair execution matches:      4/20
Run 004 + semantic repair execution matches:  5/20

Raw Run 004 predicted SQL executes:                 5/20
Run 004 + alias repair predicted SQL executes:     8/20
Run 004 + join repair predicted SQL executes:      11/20
Run 004 + semantic repair predicted SQL executes:  11/20
```

Failure pattern after semantic repair:

```text
executes_wrong_result: 6
wrong_table_for_column: 6
execution_match: 5
invented_column: 3
```

## New Success

Question 733 in the `superhero` database improved from a wrong executable
result to an execution match.

Original prediction:

```sql
SELECT COUNT(T1.id)
FROM superhero AS T1
INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id
WHERE T2.publisher_name = 'Marvel Comics'
  AND T1.eye_colour_id = 'Gold'
```

Repaired prediction:

```sql
SELECT COUNT(T1.id)
FROM superhero AS T1
INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id
INNER JOIN colour AS T3 ON T1.eye_colour_id = T3.id
WHERE T2.publisher_name = 'Marvel Comics'
  AND T3.colour = 'Gold'
```

## Lesson

This is the second repair layer that improved correctness. The first one fixed
missing joins for invalid SQL. This one fixed a query that already executed but
had the wrong meaning.

The important technical idea is that execution success is not enough. A query
can be valid SQL and still ask the database the wrong semantic question.

## Next Step

The next useful direction is targeted value canonicalization. One remaining
example uses:

```text
status = 'legal'
```

when the database value is:

```text
status = 'Legal'
```

That kind of repair should only happen when a column contains exactly one
case-insensitive match for the generated literal.

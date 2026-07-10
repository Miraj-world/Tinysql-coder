# SQL Repair Experiment 002

Date: 2026-07-09

## Goal

Extend the Run 004 repair pass from alias-only repair to conservative
join-aware repair.

## Why

The alias-only repair made more predictions executable, but it did not improve
execution matches. The next common failure was:

```text
The model used a real column, but the table containing that column was missing
from the query.
```

## Script

```text
scripts/repair_sql_predictions.py
```

## Method

The repair pass now has two layers:

```text
1. Alias repair
   wrong_alias.column -> correct_alias.column
   Only when the correct table is already present.

2. Join repair
   wrong_alias.column -> new_alias.column
   Add the missing table only when:
   - exactly one table owns the missing column
   - that table has a direct foreign-key join to a table already in the query
   - the SQL does not contain nested SELECTs
```

The join repair is intentionally conservative. It does not try to invent
multi-hop joins or rewrite the whole query.

## Result

```text
Raw Run 004 execution matches:             3/20
Run 004 + alias repair execution matches: 3/20
Run 004 + join repair execution matches:  4/20

Raw Run 004 predicted SQL executes:             5/20
Run 004 + alias repair predicted SQL executes: 8/20
Run 004 + join repair predicted SQL executes:  11/20
```

Failure pattern after join repair:

```text
executes_wrong_result: 7
wrong_table_for_column: 6
execution_match: 4
invented_column: 3
```

## New Success

Question 736 in the `superhero` database improved from an execution error to
an execution match.

The model originally wrote:

```sql
WHERE T2.attribute_name = 'Intelligence'
```

But `attribute_name` belongs to the `attribute` table, not `hero_attribute`.
The repair added:

```sql
INNER JOIN attribute AS T3 ON T2.attribute_id = T3.id
```

and rewrote the filter to:

```sql
WHERE T3.attribute_name = 'Intelligence'
```

## Lesson

Join-aware repair is the first post-generation guardrail that improved answer
correctness, not just SQL executability.

The remaining problem is that runnable SQL can still be semantically wrong.
For example, adding a missing lookup table can fix a column error while leaving
an unnecessary wrong table or a wrong literal comparison in place.

## Next Step

Add a stricter semantic repair layer for lookup-table literals, such as:

```text
T1.eye_colour_id = 'Gold'
```

to:

```text
JOIN colour AS T3 ON T1.eye_colour_id = T3.id
WHERE T3.colour = 'Gold'
```

That targets the next class of failures where the SQL executes but compares an
ID column directly to a human-readable value.

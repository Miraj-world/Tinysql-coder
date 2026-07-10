# SQL Repair Experiment 005

Date: 2026-07-10

## Goal

Try a guarded wrong-join pruning repair and a duplicate-projection repair.

## Why

After value canonicalization, one remaining query still returned the wrong rows
because it joined an unnecessary table and produced duplicate IDs.

The predicted query used:

```sql
FROM Team AS T1
INNER JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id
```

But the question only needed columns from `Team_Attributes`.

## Script

```text
scripts/repair_sql_predictions.py
```

## Method

Two conservative repair layers were added:

```text
1. Leading join pruning
   Remove a leading INNER JOIN table only when:
   - the SQL has no nested SELECT
   - the join condition is a simple alias.column = alias.column equality
   - the removed alias is not referenced outside the join condition
   - the repaired SQL still executes

2. DISTINCT repair
   Add DISTINCT only when:
   - the SQL has no nested SELECT
   - the SQL has no aggregate and no GROUP BY
   - the SELECT list is one qualified column
   - the current result contains duplicate rows
   - the repaired SQL still executes
```

The repair does not use the gold SQL to decide whether to apply.

## Result

```text
Raw Run 004 execution matches:                 3/20
Run 004 + alias repair execution matches:     3/20
Run 004 + join repair execution matches:      4/20
Run 004 + semantic repair execution matches:  5/20
Run 004 + value repair execution matches:     6/20
Run 004 + distinct repair execution matches:  7/20

Run 004 + distinct repair predicted SQL executes: 11/20
```

Failure pattern after distinct repair:

```text
execution_match: 7
wrong_table_for_column: 6
executes_wrong_result: 4
invented_column: 3
```

## New Success

Question 1035 in the `european_football_2` database improved from wrong
executable result to execution match.

Before repair:

```sql
SELECT T2.team_fifa_api_id
FROM Team AS T1
INNER JOIN Team_Attributes AS T2 ON T1.team_api_id = T2.team_api_id
WHERE T2.buildUpPlaySpeed > 50
  AND T2.buildUpPlaySpeed < 60
```

After repair:

```sql
SELECT DISTINCT T2.team_fifa_api_id
FROM Team_Attributes AS T2
WHERE T2.buildUpPlaySpeed > 50
  AND T2.buildUpPlaySpeed < 60
```

## Lesson

Some text-to-SQL failures are not missing-table problems. They are over-join
problems: the model adds a plausible table that changes row multiplicity.

The useful insight is that repair can be layered:

```text
first remove the unused join
then notice the simple projection still has duplicate rows
then add DISTINCT
```

## Next Step

The remaining failures are harder. The next useful direction is a table
replacement experiment for cases where the model chose a plausible but wrong
fact table, such as `Team` instead of `Match`. That should be separate because
table replacement is much riskier than pruning an unused join.

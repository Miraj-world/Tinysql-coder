# SQL Repair Experiment 004

Date: 2026-07-10

## Goal

Add targeted value canonicalization to the Run 004 SQL repair pass.

## Why

After semantic lookup repair, one remaining query had the right column but the
wrong string casing:

```text
status = 'legal'
```

The database value is:

```text
status = 'Legal'
```

SQLite string comparison is case-sensitive for normal equality checks, so this
small value mismatch can change the result.

## Script

```text
scripts/repair_sql_predictions.py
```

## Method

Value repair only applies when:

```text
- the SQL already executes
- the query has a qualified string comparison like alias.column = 'value'
- the referenced alias and column exist in the SQL schema
- the database contains exactly one distinct case-insensitive match
- that match differs from the generated value
- the repaired SQL still executes
```

The repair does not guess values. It asks the SQLite database for an exact
case-insensitive match and only rewrites when there is one unambiguous answer.

## Result

```text
Raw Run 004 execution matches:              3/20
Run 004 + alias repair execution matches:  3/20
Run 004 + join repair execution matches:   4/20
Run 004 + semantic repair execution matches: 5/20
Run 004 + value repair execution matches:  6/20

Run 004 + value repair predicted SQL executes: 11/20
```

Failure pattern after value repair:

```text
execution_match: 6
wrong_table_for_column: 6
executes_wrong_result: 5
invented_column: 3
```

## New Success

Question 415 in the `card_games` database improved from wrong executable result
to execution match.

The repair changed:

```sql
T3.status = 'legal'
```

to:

```sql
T3.status = 'Legal'
```

because `Legal` was the single case-insensitive match in the `legalities.status`
column.

## Lesson

Small value mismatches matter in text-to-SQL. Once a generated query has the
right table and column, the next failure can be the exact database spelling or
casing of the value.

This repair is narrow but useful because it relies on the database itself
instead of guessing from natural language.

## Next Step

The next useful repair direction is wrong-join pruning or table replacement.
Some remaining queries execute but include an unnecessary or wrong table join.
That is riskier than value canonicalization because removing joins can change
row multiplicity and filters, so it should be explored with a separate guarded
experiment.

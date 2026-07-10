# SQL Repair Experiment 006

Date: 2026-07-10

## Goal

Try a guarded table-replacement/table-split repair for remaining schema
grounding failures.

## Why

After DISTINCT repair, the remaining failures were mostly harder cases:

```text
wrong table for a column
invented plausible column
wrong fact table
SQL executes but returns the wrong rows
```

The next hypothesis was that some bad SQL could be repaired by adding the
table that actually owns a referenced column, then moving only that column
reference to the new table alias.

## Script

```text
scripts/repair_sql_predictions.py
```

## Method

Two targeted improvements were made:

```text
1. Foreign-key primary-key inference
   Some SQLite foreign keys point to a table but omit the target column.
   When the target table has exactly one primary-key column, the repair layer
   now infers that primary key and can use the relationship.

2. Quoted qualified-column replacement
   The alias replacement code now handles quoted column references such as
   T1.`Consumption`, not only unquoted references such as T1.consumption.
```

The repair still does not use gold SQL to decide what to change.

## Result

```text
Run 004 + distinct repair execution matches: 7/20
Run 004 + table repair execution matches:    7/20

Run 004 + table repair predicted SQL executes: 11/20
```

Failure pattern after table repair:

```text
execution_match: 7
wrong_table_for_column: 6
executes_wrong_result: 4
invented_column: 3
```

## Important Example

Question 1526 in `debit_card_specializing` showed the limit of this approach.

The repair correctly noticed that `Consumption` belongs to `yearmonth`, not
`customers`, and added:

```sql
INNER JOIN yearmonth AS T3 ON t1.customerid = T3.customerid
```

It also changed:

```sql
T1.`Consumption`
```

to:

```sql
t3.`Consumption`
```

But the query still did not become correct. The gold SQL needs a different
query shape: year-based aggregation and a subquery that identifies the customer
from a transaction/gas-station condition.

## Lesson

This was a useful negative result.

Local schema repair can fix small ownership errors, but it cannot safely
reconstruct a missing analytical plan. When the model has the wrong query
shape, a repair pass should not guess its way into a much larger rewrite.

## Next Step

Move the next improvement back into data/prompting:

```text
Create an error-aware SFT V6 dataset from failed Run 004 examples.
Teach the model to distinguish:
- local alias/column ownership fixes
- lookup/value fixes
- wrong fact-table/query-shape failures that require a new plan
```

The target is not more free-form reasoning. The target is shorter, structured
planning that helps the model choose the correct fact table before writing SQL.

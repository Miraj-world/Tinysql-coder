# SQL Repair Experiment 010 - Exact Syntax Fragment

Date: 2026-07-14

## Goal

Repair the exact invalid SQL token sequence:

```sql
IS NOT IN
```

to the valid SQL operator:

```sql
NOT IN
```

The rule runs only when SQLite reports a syntax error near `IN` and the invalid
sequence is actually present.

## Why This Is Safe

`IS NOT IN` is not a competing SQL operator with a different meaning. It is an
invalid mixture of `IS NOT` and `NOT IN`. Therefore, this repair corrects a
known syntax form instead of choosing between tables, columns, or query plans.

Three new tests verify the correction and ensure it does not run for unrelated
errors or already-valid `NOT IN` syntax. The complete repair suite now contains
18 passing tests.

## Evaluation

| Run | Execution matches | Predicted SQL that ran | Change from Experiment 009 |
| --- | ---: | ---: | ---: |
| 004 + repair | 7/20 | 11/20 | no change |
| 007 + repair | 6/20 | 12/20 | one more query ran |
| 008 + repair | 3/20 | 9/20 | no change |

The rule activated on Run 007 Q212:

```text
IS NOT IN -> NOT IN
```

Before repair, SQLite rejected the query. After repair, it executed and
returned `h`. The gold SQL returned `ca`, so this was not an execution match.

## Lesson

Syntax repair can make malformed SQL runnable, but it cannot repair a wrong
aggregation or missing join. This experiment improved executability without
improving answer accuracy.

Across Experiments 007-010, conservative repair increased the number of SQL
statements that run in specific cases, but none of the new rules increased the
best execution-match score. The best overall result remains Run 004 plus repair
at 7/20.

## Decision

The recent bottleneck is semantic rather than syntactic. The next major step
should return to model or training-data improvement, using the focused error
set as evidence, rather than adding increasingly speculative repair rules.

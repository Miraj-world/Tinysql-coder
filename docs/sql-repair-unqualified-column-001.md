# SQL Repair Experiment 007 - Guarded Unqualified Columns

Date: 2026-07-14

## Goal

Test one narrow post-generation repair:

```text
When SQLite reports a bare missing column and exactly one table already joined
in the same flat query owns that column, add that table's alias.
```

Example:

```sql
WHERE height > 180
```

becomes:

```sql
WHERE p.height > 180
```

only when `p` is the single joined alias whose table contains `height`.

## Safety Guards

The repair does nothing when:

- the query contains a nested `SELECT`, because aliases have separate scopes;
- fewer than two tables are present;
- more than one joined table owns the column;
- the error already contains a qualified name such as `T1.id`;
- the matching word is inside a string literal or is already qualified.

Five unit tests cover the successful case and these rejection cases.

## Evaluation

The updated repair stack was rerun on the 20 predictions from Runs 004, 007,
and 008. Each repaired prediction was executed against its real SQLite
database and its returned rows were compared with the gold SQL rows.

| Run | Execution matches | Predicted SQL that ran | New-rule activations |
| --- | ---: | ---: | ---: |
| 004 + repair | 7/20 | 11/20 | 0 |
| 007 + repair | 6/20 | 11/20 | 0 |
| 008 + repair | 3/20 | 8/20 | 0 |

## Why It Activated Zero Times

The six focused examples grouped as `ambiguous_or_unqualified_column` are not
six instances of the same mechanical bug:

- Q1058 and Q733 use bare columns inside nested queries. Qualifying them with
  an outer alias would cross a query boundary and could change the meaning.
- Q928 is a malformed derived table with no valid source table inside it.
- Q884 and Q710 use aliases that were never declared.
- Q1028 contains several undeclared or wrongly assigned aliases, not one bare
  column with one clear owner.

Therefore, zero activations is the correct guarded outcome. The repair passed
its synthetic tests, but the current real prediction set contains no example
that meets its full safety rule.

## Lesson

A category label is useful for finding related failures, but it does not prove
that one repair can safely fix every example in that category. Unit tests show
that the rule works when its assumptions are true. Execution evaluation shows
whether those assumptions occur in real model output.

The best overall result remains Run 004 plus the existing repair stack at
7/20 execution matches.

## Next Candidate

The next focused coding experiment should target undeclared aliases in flat
queries. A safe first rule would require that the missing alias-qualified
column has exactly one owner among tables already present in the same flat
query. Nested derived tables and queries with multiple broken aliases should
remain out of scope.

This candidate was implemented and evaluated in
[SQL Repair Experiment 008](sql-repair-undeclared-alias-001.md).

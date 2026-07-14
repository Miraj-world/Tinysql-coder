# SQL Repair Experiment 008 - Guarded Undeclared Aliases

Date: 2026-07-14

## Goal

Repair a qualified column reference whose alias was never declared, but only
when exactly one table already present in the same flat query owns the column.

Example:

```sql
SELECT T1.name FROM players
```

becomes:

```sql
SELECT players.name FROM players
```

when `players` is the only in-scope table containing `name`.

## Why This Is Guarded

An alias is a short name assigned to a table. In this example, `T1` is used
without an `AS T1` declaration, so SQLite cannot determine what `T1.name`
means.

The repair refuses to guess when:

- the query contains a nested `SELECT`;
- the alias is already declared;
- no table currently in the query owns the column; or
- multiple in-scope tables own the column.

Five new tests cover the successful case and these rejection cases. Together
with the previous experiment, the repair test suite now contains ten tests.

## Evaluation

The complete repair stack was rerun on Runs 004, 007, and 008.

| Run | Execution matches | Predicted SQL that ran | Change from Experiment 007 |
| --- | ---: | ---: | ---: |
| 004 + repair | 7/20 | 11/20 | no change |
| 007 + repair | 6/20 | 11/20 | no change |
| 008 + repair | 3/20 | 9/20 | one more query ran |

The new rule activated twice in Run 008:

### Q884

```text
T.name -> races.name
```

The repaired SQL executed, but returned the wrong rows because its date logic
did not match the question. This changed the failure from an execution error
to an executable wrong answer.

### Q710

```text
T1.id -> comments.id
```

This fixed the first error. A second error then appeared because
`CommentCount` belongs to `posts`, which is not present in the query. The SQL
still did not execute.

## Lesson

There are two separate measurements:

1. **Executable SQL** means SQLite can run the query.
2. **Execution match** means the query returns the same rows as the correct SQL.

Making one more query executable is useful diagnostic progress, but it is not
an accuracy improvement. The best result therefore remains Run 004 plus repair
at 7/20 execution matches.

## Next Candidate

Q710 exposes the next narrow mechanical problem: a column belongs to one table
that is missing from a flat query. Before adding a table, the repair must find
exactly one direct foreign-key join from an existing table. This resembles the
existing qualified-column join repair and can be extended to bare columns
without guessing across nested scopes.

# SQL Repair Experiment 009 - Guarded Bare-Column Join

Date: 2026-07-14

## Goal

Extend join repair to a bare missing column when:

- exactly one table in the database owns the column;
- that owner table is not already in the flat query; and
- exactly one direct foreign-key relationship connects it to a table already
  in the query.

The repair adds the table through that declared relationship and qualifies the
bare column with a new alias.

## Example

Starting SQL:

```sql
SELECT COUNT(comments.id)
FROM comments
WHERE CommentCount = 1
```

Schema facts:

```text
posts is the only table that owns CommentCount
comments.postid references posts.id
```

Repaired SQL:

```sql
SELECT COUNT(comments.id)
FROM comments
INNER JOIN posts AS T1 ON comments.postid = T1.id
WHERE T1.CommentCount = 1
```

## Safety Guards

The rule rejects nested queries, columns already owned by an in-scope table,
columns with multiple database owners, and missing or multiple possible
foreign-key paths.

Five new tests cover the accepted case and rejection cases. The repair suite
now contains 15 passing tests.

## Evaluation

| Run | Execution matches | Predicted SQL that ran | Change from Experiment 008 |
| --- | ---: | ---: | ---: |
| 004 + repair | 7/20 | 11/20 | no change |
| 007 + repair | 6/20 | 11/20 | no change |
| 008 + repair | 3/20 | 9/20 | no change |

The new rule activated on Run 008 Q710 after the undeclared-alias repair fixed
its first error:

```text
T1.id -> comments.id
added posts AS T1 ON comments.postid = T1.id
CommentCount -> T1.CommentCount
```

The resulting query then failed with:

```text
ambiguous column name: Score
```

Both `comments` and `posts` own a `Score` column. Schema ownership alone cannot
prove which one the question means, so the repair correctly stopped instead of
guessing.

## Lesson

SQL repair is iterative. Fixing the first database error can expose the next
one. A successful mechanical repair does not guarantee a correct final query;
every layer must preserve meaning.

This experiment improved the structure of Q710 but did not improve execution
accuracy or the number of executable queries. The best result remains Run 004
plus repair at 7/20 execution matches.

## Next Candidate

Do not automatically resolve an ambiguous column just because one table was
recently added. That would be a weak guess. The next experiment should inspect
the remaining syntax and execution errors for a rule supported by stronger
evidence.

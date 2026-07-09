# Failure Pattern Analysis 004

Date: 2026-07-09

## Goal

Analyze LoRA Run 004 failures.

## Result

```text
wrong_table_for_column: 12
invented_column: 3
execution_match: 3
executes_wrong_result: 2
```

## Comparison

```text
Run 003 execution matches: 2
Run 004 execution matches: 3

Run 003 predicted SQL executed: 4
Run 004 predicted SQL executed: 5
```

## Lesson

The score improved, but `wrong_table_for_column` is still the dominant failure.

Example:

```text
column `element` was referenced on `molecule`, but exists on `atom`
```

So the model still needs stronger table-column ownership supervision. More
oversampling helps a little, but it may not be enough.

## Next Step

Inspect the hard failures and consider teacher-generated examples that directly
teach:

```text
needed columns -> owning tables -> join path -> final SQL
```

# Eval 009 - LoRA Run 005

Date: 2026-07-09

## Goal

Evaluate LoRA Run 005 against the fixed 20-example evaluation question set,
using the V5 ownership-teacher prompt style.

## Result

```text
Total examples: 20
Exact matches: 0/20
Execution matches: 0/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 1/20
```

## Comparison

```text
Base Qwen execution matches: 1/20
LoRA Run 001 execution matches: 0/20
LoRA Run 002 execution matches: 0/20
LoRA Run 003 execution matches: 2/20
LoRA Run 004 execution matches: 3/20
LoRA Run 005 execution matches: 0/20
```

Run 004 remains the best checkpoint.

## What Happened

The V5 reasoning target did not improve schema grounding. It also made some
generations unstable: a few outputs emitted ownership notes without reaching
clean final SQL.

Failure analysis:

```text
wrong_table_for_column: 10
invented_column: 3
execution_error_other: 3
ambiguous_or_unqualified_column: 2
hallucinated_table: 1
executes_wrong_result: 1
```

## Lesson

Free-form ownership reasoning is not the next good direction for this small
model and short training budget.

The next attempt should keep the assistant target SQL-only and instead add
more constrained supervision, such as:

```text
1. better schema-linking prompt text at inference time
2. hard negative examples that contrast wrong table vs correct table
3. post-generation SQL repair using the schema before execution
```

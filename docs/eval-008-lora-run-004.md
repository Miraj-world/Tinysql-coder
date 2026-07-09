# Eval 008 - LoRA Run 004

Date: 2026-07-09

## Goal

Evaluate LoRA Run 004 against the fixed 20-example evaluation set.

## Result

```text
Total examples: 20
Exact matches: 0/20
Execution matches: 3/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 5/20
```

## Comparison

```text
Base Qwen execution matches: 1/20
LoRA Run 001 execution matches: 0/20
LoRA Run 002 execution matches: 0/20
LoRA Run 003 execution matches: 2/20
LoRA Run 004 execution matches: 3/20
```

Run 004 is the best run so far.

## What Improved

Run 004 produced three execution matches:

```text
question_id 555  - simple two-table join
question_id 791  - simple single-table aggregate
question_id 1394 - simple two-table join
```

## Lesson

Hard-join oversampling improved the score, but the successful examples are
still simple.

That means the model is learning join mechanics gradually, but still struggles
with the hard cases we originally targeted.

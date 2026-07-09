# Failure Pattern Analysis 003

Date: 2026-07-09

## Goal

Analyze the failure pattern after LoRA Run 003.

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\analyze_failure_patterns.py --eval-path outputs\lora-run-003\execution_eval.jsonl --output-path outputs\analysis\lora-run-003-failure-analysis.md
```

## Result

```text
wrong_table_for_column: 13
execution_match: 2
executes_wrong_result: 2
ambiguous_or_unqualified_column: 1
hallucinated_table: 1
invented_column: 1
```

## Comparison

```text
Run 002 execution matches: 0
Run 003 execution matches: 2

Run 002 predicted SQL executed: 1
Run 003 predicted SQL executed: 4
```

The wrong-table-column category is still large, but Run 003 produced more SQL
that could actually execute and two correct-by-execution answers.

## Lesson

Oversampling join examples improved execution behavior, but did not fully solve
schema grounding.

Next we should inspect the two successful examples and the remaining
wrong-table-column cases. If the successful examples are join-related, that is
evidence to continue join-focused training with either more steps or better
teacher-generated join examples.

# Failure Pattern Analysis 002

Date: 2026-07-09

## Goal

Compare the failure pattern after LoRA Run 002 to LoRA Run 001.

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\analyze_failure_patterns.py --eval-path outputs\lora-run-002\execution_eval.jsonl --output-path outputs\analysis\lora-run-002-failure-analysis.md
```

## Result

```text
wrong_table_for_column: 11
ambiguous_or_unqualified_column: 3
hallucinated_table: 2
invented_column: 2
executes_wrong_result: 1
execution_error_other: 1
```

## Comparison Against Run 001

```text
Run 001 wrong_table_for_column: 13
Run 002 wrong_table_for_column: 11
```

This is a small movement in the right direction, but not enough to improve
execution accuracy.

## Lesson

SFT V2 targeted the right weakness, but the first short run is still too weak.

The next improvement should likely be one of:

```text
1. Train longer on SFT V2.
2. Add SQL planning/rationale supervision before final SQL.
3. Generate extra teacher examples focused on joins and table-column ownership.
```

Because the current dataset has only 400 training examples, teacher-generated
join-focused examples may be more useful than simply increasing steps.

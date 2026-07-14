# Focused Repair Error Set 001

Date: 2026-07-14

## Goal

After Run 008, another label-format experiment looked less promising than a
smaller post-generation repair pass. The next step was to collect the remaining
mechanically interesting failures into one focused error set.

## What Changed

Added `scripts/create_focused_error_set.py`.

The script reads repaired execution-eval files, reuses the existing failure
classifier, and keeps only categories that might support a guarded SQL repair:

- `wrong_table_for_column`
- `ambiguous_or_unqualified_column`
- `execution_error_other`
- `invented_column`
- `hallucinated_table`

It intentionally excludes `executes_wrong_result`. Those queries already run,
but answer the wrong question, so they usually need better semantic generation
rather than a safe string-level repair.

## Inputs

- `outputs/lora-run-004-table-repaired/execution_eval.jsonl`
- `outputs/lora-run-007-repaired/execution_eval.jsonl`
- `outputs/lora-run-008-repaired/execution_eval.jsonl`

## Result

The focused set contains 30 examples:

| Category | Count |
|---|---:|
| `wrong_table_for_column` | 12 |
| `invented_column` | 7 |
| `ambiguous_or_unqualified_column` | 6 |
| `execution_error_other` | 4 |
| `hallucinated_table` | 1 |

By run:

| Run | Count |
|---|---:|
| `lora-run-008-repaired` | 12 |
| `lora-run-004-table-repaired` | 9 |
| `lora-run-007-repaired` | 9 |

Generated artifacts:

- `outputs/analysis/focused-repair-error-set.jsonl`
- `outputs/analysis/focused-repair-error-set.md`

## Decision

The next repair should focus on a narrow, measurable rule from this set. The
best first candidate is likely unqualified-column repair: when SQLite reports a
bare column name and exactly one joined table owns that column, qualify it with
the correct alias and rerun evaluation.

That is safer than trying to repair invented columns, because invented-column
examples often require changing the whole query plan.

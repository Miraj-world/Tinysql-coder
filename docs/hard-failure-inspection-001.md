# Hard Failure Inspection 001

Date: 2026-07-09

## Goal

Inspect the remaining hard failures after LoRA Run 004.

## Why

Run 004 improved to:

```text
Execution matches: 3/20
Predicted SQL executed: 5/20
```

But most remaining errors still come from table-column ownership mistakes.

## Script

```text
scripts/inspect_hard_failures.py
```

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\inspect_hard_failures.py
```

Default local report:

```text
outputs/analysis/lora-run-004-hard-failures.md
```

## Main Pattern

The next training format should teach this sequence explicitly:

```text
needed columns -> owning tables -> join path -> final SQL
```

Examples from Run 004:

```text
element belongs to atom, not molecule
format belongs to legalities, not cards
attribute_name belongs to attribute, not hero_attribute
```

## Lesson

Oversampling improved the score, but the model still does not reliably perform
the schema reasoning step before writing SQL.

Run 005 should probably introduce explicit planning supervision, not just more
copies of the same final SQL examples.

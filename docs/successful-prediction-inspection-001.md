# Successful Prediction Inspection 001

Date: 2026-07-09

## Goal

Inspect the two LoRA Run 003 predictions that matched by execution.

## Why

When a run improves, we should study what worked, not only what failed.

Run 003 reached:

```text
Execution matches: 2/20
Predicted SQL executed successfully: 4/20
```

## Script

```text
scripts/inspect_successful_predictions.py
```

## Command

```powershell
.\.venv312\Scripts\python.exe scripts\inspect_successful_predictions.py
```

Default local report:

```text
outputs/analysis/lora-run-003-successes.md
```

The report stays local because `outputs/` is ignored by Git.

## Successful Examples

### Question 791

Database:

```text
superhero
```

Pattern:

```text
single-table aggregate
```

Predicted SQL:

```sql
SELECT CAST(SUM(T1.height_cm) AS REAL) / COUNT(T1.id) FROM superhero AS T1
```

Gold SQL:

```sql
SELECT CAST(SUM(height_cm) AS REAL) / COUNT(id) FROM superhero
```

This is not an exact string match, but it returns the same row.

### Question 1394

Database:

```text
student_club
```

Pattern:

```text
simple two-table join
```

Predicted SQL:

```sql
SELECT COUNT(T1.member_id)
FROM member AS T1
INNER JOIN major AS T2 ON T1.link_to_major = T2.major_id
WHERE T2.major_name = 'Physics Teaching'
```

Gold SQL:

```sql
SELECT COUNT(T2.member_id)
FROM major AS T1
INNER JOIN member AS T2 ON T1.major_id = T2.link_to_major
WHERE T1.major_name = 'Physics Teaching'
```

The join order is different, but the relationship is equivalent.

## Lesson

Run 003's improvement came from simple cases:

```text
1. A clean single-table aggregate.
2. A simple two-table join with the right key relationship.
```

This supports the idea that join-focused training helped, but only on simpler
join structures.

## Next Step

Run 004 should target moderate and challenging join patterns, especially:

```text
multi-table joins
subqueries
columns with similar names across tables
```

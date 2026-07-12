# Schema Guidance Quality 001

Date: 2026-07-12

## Goal

Improve schema guidance by removing noisy join hints.

## Why

Run 006 showed that a new reasoning format was not enough. The prompts still
contained bad join hints such as:

```text
Country.id = Player.id
circuits.url = drivers.url
event.type = zip_code.type
```

Those hints came from matching every exact shared column name. That was too
loose. It taught the model that unrelated tables could be joined just because
they both had a generic column like `id`, `name`, `url`, or `type`.

## Script

```text
scripts/build_schema_guidance.py
```

## Change

The schema guidance builder now:

```text
1. Uses real SQLite foreign keys first.
2. Infers a missing target column when the target table has one clear primary key.
3. Adds inferred joins only for specific identifier-like shared columns.
4. Rejects generic shared columns such as id, name, date, type, status, url, and points.
5. Deduplicates join hints even when the same join appears in the opposite direction.
```

## Example

The `student_club` guidance is now focused on real relationships:

```text
attendance.link_to_event = event.event_id
attendance.link_to_member = member.member_id
budget.link_to_event = event.event_id
expense.link_to_budget = budget.budget_id
expense.link_to_member = member.member_id
income.link_to_member = member.member_id
member.link_to_major = major.major_id
member.zip = zip_code.zip_code
```

It no longer includes noisy hints like:

```text
budget.amount = income.amount
event.notes = income.notes
event.type = zip_code.type
```

## Join Hint Counts After Cleanup

```text
california_schools: 2
card_games: 10
codebase_community: 25
debit_card_specializing: 5
european_football_2: 32
financial: 15
formula_1: 56
student_club: 8
superhero: 12
thrombosis_prediction: 2
toxicology: 6
```

## Follow-Up

Regenerated local artifacts:

```text
data/bird_mini_dev/schema/schema_guidance.json
data/bird_mini_dev/sft_v6/train_sft_v6.jsonl
data/bird_mini_dev/sft_v6/validation_sft_v6.jsonl
outputs/lora-run-007/eval_set.jsonl
```

These files are local/generated and ignored by Git. The script change is the
tracked source of truth.

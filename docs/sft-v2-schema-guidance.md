# SFT V2 Schema Guidance

Date: 2026-07-09

## Goal

Create a stronger SFT format for LoRA Run 002.

## Why

Failure Pattern Analysis 001 showed the dominant error:

```text
wrong_table_for_column: 13/20
```

So the next dataset should teach table-column ownership more explicitly.

## New Scripts

Build schema guidance:

```text
scripts/build_schema_guidance.py
```

Prepare SFT V2 data:

```text
scripts/prepare_sft_data_v2.py
```

## What Changed

The original SFT data included compact schema text like:

```text
cards(id, uuid, hasContentWarning, ...)
legalities(id, format, status, uuid)
```

SFT V2 adds a more explicit section:

```text
Column ownership:
cards: id, uuid, hasContentWarning, ...
legalities: id, format, status, uuid

Possible join keys:
cards.uuid = legalities.uuid
```

## Lesson

This does not magically solve text-to-SQL.

But it directly targets the biggest observed failure:

```text
putting columns on the wrong table
```

LoRA Run 002 should train on this V2 format.

## Token Length Check

SFT V2 is longer than V1 because it repeats table-column ownership and join
hints.

Latest token check:

```text
examples: 500
min tokens: 315
max tokens: 2282
average tokens: 1069.5
examples over 2048 tokens: 52
examples over 3072 tokens: 0
```

Run 002 should use:

```text
max_sequence_length: 3072
```

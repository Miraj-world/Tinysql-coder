# Database Value Retrieval V1

Date: 2026-07-14

## Purpose

Run 013 plus repair makes 90/100 predictions executable but only 34/100
correct. The new project-best cascade executes 98/100 but reaches 36/100. The
remaining problem is mostly meaning, not broken SQL.

The value retriever reads the natural-language question, its provided evidence,
and the target SQLite database. It never reads the expected SQL.

## Safety Rules

- match complete words or phrases, not arbitrary substrings;
- require numbers and short codes to match a relevant full column name;
- ignore binary and very long values;
- cap retrieval at eight columns and five values per column;
- scan each database once and reuse the cached values for its questions;
- preserve the original expected SQL and evaluation records unchanged.

## Verification

```text
automated tests:                 46 passed
evaluation records:             100
records with value hints:        88
retrieved column/value lines:   279
gold SQL used by retrieval:      no
```

The next measurement is to run the same Run 013 adapter on these augmented
prompts and compare execution accuracy against its 28/100 raw and 34/100
repaired scores.

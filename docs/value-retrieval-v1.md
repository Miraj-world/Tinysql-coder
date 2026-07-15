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

## Measured Result

| System | Execution matches | SQL executed |
|---|---:|---:|
| Run 013 | 28/100 | 75/100 |
| Run 013 + repair | 34/100 | 90/100 |
| Run 013 + retrieved values | 29/100 | 76/100 |
| Run 013 + retrieved values + repair | **35/100** | 89/100 |
| Value-guided Run 013 with execution-only fallbacks | **39/100** | **99/100** |

Retrieval provides a small direct improvement and complementary predictions
that make the safe cascade three points better. V10 now tests whether training
the adapter to understand the value-context section can increase that gain.

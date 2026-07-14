# Filtered BIRD Training Pivot

Date: 2026-07-14

## Why We Changed the Data

Runs 001 through 010 repeatedly trained on the same 400 unique mini-dev
questions. Oversampling changed how often the model saw certain examples, but
it did not add much new language-to-SQL knowledge.

The BIRD team released a filtered training split containing 6,601 curated
question/SQL pairs from 69 training databases. Their dataset card reports that
this subset retained examples checked for schema consistency and faithful
question answering. We therefore changed from repeating 400 examples to using
genuinely different training questions and schemas.

Official data source:

- <https://huggingface.co/datasets/birdsql/bird23-train-filtered>

The official table/foreign-key file is bundled with a database archive that is
almost 9 GB compressed. For the relationship-guided follow-up, the project uses
a pinned 158 KB mirror of the standard BIRD `train_tables.json` file:

- <https://huggingface.co/datasets/Deema/BIRD-SQL>

This mirror is not maintained by the BIRD team. Before use, the downloader
checks that its schemas cover exactly the same 69 database IDs as the official
filtered rows. The pinned revision makes the experiment reproducible.

## Leakage Guards

The preparation scripts enforce three important rules:

1. Mini-dev remains evaluation-only.
2. Training and internal validation are split by whole database, not random
   rows.
3. Exact question overlap between the 6,601 training rows and mini-dev must be
   zero.

Verified preparation result:

```text
source rows:                     6,601
training rows:                   5,825
internal validation rows:          776
training databases:                 62
internal validation databases:       7
database overlap:                     0
exact mini-dev question overlap:      0
```

Splitting by database is stricter than splitting by question. The model cannot
get a good internal validation loss merely by memorizing the schema of a
database that also appears in training.

## V8 Format

V8 uses compact `table(column, ...)` schemas, question evidence, and a plain SQL
answer. It removes the older `PLAN_TYPE` and `FINAL_SQL` labels so training and
inference both ask for the same thing: SQL only.

At 2,048 tokens, all 6,601 V8 examples fit without truncation.

## V9 Relationship Format

Run 011 showed that compact schemas alone did not teach joins reliably. Adding
verified join keys only at inference improved repaired execution accuracy from
19/100 to 24/100. V9 therefore adds foreign-key relationships during training
as well.

Long databases can contain many relationships, so V9 caps guidance at 12
deterministically ordered join lines. A 2,080-token window then covers every
training and validation example without cutting off the gold SQL.

## What This Change Does Not Reproduce

The BIRD team's published training result is not directly comparable to this
laptop experiment. Their documented recipe uses:

- Qwen2.5-3B rather than Qwen2.5-Coder-1.5B;
- two full epochs rather than a partial epoch;
- database-value retrieval with a BM25 index;
- much longer sequence lengths, up to 18,000 tokens;
- four GPUs rather than one 8 GB laptop GPU.

This project tested the most practical data improvement that fits locally. It
did not reproduce the full published system.

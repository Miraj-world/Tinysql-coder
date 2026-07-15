# Evaluation Journal

This folder records model evaluation results, setup checkpoints, failures, lessons, and next steps.

Raw generated artifacts live under `outputs/`. These markdown files are for human interpretation.

## Current Snapshot

As of 2026-07-15, the final practical Run 013 pipeline has been tested once on
100 previously unseen BIRD questions. It reached 36/100 execution matches raw
and **43/100 after the unchanged guarded repair pipeline**. Repaired SQL
executed successfully for 83/100 questions. See
[Eval 019](eval-019-unseen-bird-dev.md).

The earlier gold-free semantic judge remains the best development-benchmark
system at 46/100, but it uses a much more expensive ten-source candidate pool.
That score and the 43/100 unseen single-model score describe different systems
and should not be treated as a direct comparison. Model experimentation is now
stopped.

Historical "Next Step" sections below record what was learned at that point in
the project; later entries supersede them rather than rewriting the history.

## Entries

| Date | Entry | File |
|---|---|---|
| 2026-07-08 | Baseline Eval 001 | [eval-001-baseline.md](eval-001-baseline.md) |
| 2026-07-08 | Schema Availability Check | [schema-availability-check.md](schema-availability-check.md) |
| 2026-07-08 | Database Package Added | [database-package-added.md](database-package-added.md) |
| 2026-07-08 | Schema Text Extraction | [schema-text-extraction.md](schema-text-extraction.md) |
| 2026-07-08 | Schema-Informed Baseline Eval 002 | [eval-002-schema-informed-baseline.md](eval-002-schema-informed-baseline.md) |
| 2026-07-08 | Execution-Based Evaluation 003 | [eval-003-execution-evaluation.md](eval-003-execution-evaluation.md) |
| 2026-07-08 | Schema-Grounding Prompt Rules 004 | [eval-004-schema-grounding-prompt.md](eval-004-schema-grounding-prompt.md) |
| 2026-07-09 | SFT Data Preparation | [sft-data-preparation.md](sft-data-preparation.md) |
| 2026-07-09 | Training Readiness Check | [training-readiness-check.md](training-readiness-check.md) |
| 2026-07-09 | LoRA Training Smoke Test | [lora-smoke-test.md](lora-smoke-test.md) |
| 2026-07-09 | LoRA Training Run 001 | [lora-training-run-001.md](lora-training-run-001.md) |
| 2026-07-09 | LoRA Run 001 Eval 005 | [eval-005-lora-run-001.md](eval-005-lora-run-001.md) |
| 2026-07-09 | Eval Comparison Tool | [eval-comparison-tool.md](eval-comparison-tool.md) |
| 2026-07-09 | Failure Analysis Tool | [failure-analysis-tool.md](failure-analysis-tool.md) |
| 2026-07-09 | Failure Pattern Analysis 001 | [failure-pattern-analysis-001.md](failure-pattern-analysis-001.md) |
| 2026-07-09 | SFT V2 Schema Guidance | [sft-v2-schema-guidance.md](sft-v2-schema-guidance.md) |
| 2026-07-09 | LoRA Training Run 002 | [lora-training-run-002.md](lora-training-run-002.md) |
| 2026-07-09 | LoRA Run 002 Eval 006 | [eval-006-lora-run-002.md](eval-006-lora-run-002.md) |
| 2026-07-09 | Failure Pattern Analysis 002 | [failure-pattern-analysis-002.md](failure-pattern-analysis-002.md) |
| 2026-07-09 | SFT V3 Join Focus | [sft-v3-join-focus.md](sft-v3-join-focus.md) |
| 2026-07-09 | LoRA Training Run 003 | [lora-training-run-003.md](lora-training-run-003.md) |
| 2026-07-09 | LoRA Run 003 Eval 007 | [eval-007-lora-run-003.md](eval-007-lora-run-003.md) |
| 2026-07-09 | Failure Pattern Analysis 003 | [failure-pattern-analysis-003.md](failure-pattern-analysis-003.md) |
| 2026-07-09 | Successful Prediction Inspection 001 | [successful-prediction-inspection-001.md](successful-prediction-inspection-001.md) |
| 2026-07-09 | SFT V4 Hard Join Focus | [sft-v4-hard-join-focus.md](sft-v4-hard-join-focus.md) |
| 2026-07-09 | LoRA Training Run 004 | [lora-training-run-004.md](lora-training-run-004.md) |
| 2026-07-09 | LoRA Run 004 Eval 008 | [eval-008-lora-run-004.md](eval-008-lora-run-004.md) |
| 2026-07-09 | Failure Pattern Analysis 004 | [failure-pattern-analysis-004.md](failure-pattern-analysis-004.md) |
| 2026-07-09 | Hard Failure Inspection 001 | [hard-failure-inspection-001.md](hard-failure-inspection-001.md) |
| 2026-07-09 | SFT V5 Ownership Teacher | [sft-v5-ownership-teacher.md](sft-v5-ownership-teacher.md) |
| 2026-07-09 | LoRA Training Run 005 | [lora-training-run-005.md](lora-training-run-005.md) |
| 2026-07-09 | LoRA Run 005 Eval 009 | [eval-009-lora-run-005.md](eval-009-lora-run-005.md) |
| 2026-07-09 | SQL Repair Experiment 001 | [sql-repair-run-004-001.md](sql-repair-run-004-001.md) |
| 2026-07-09 | SQL Repair Experiment 002 | [sql-repair-run-004-002.md](sql-repair-run-004-002.md) |
| 2026-07-09 | SQL Repair Experiment 003 | [sql-repair-run-004-003.md](sql-repair-run-004-003.md) |
| 2026-07-10 | SQL Repair Experiment 004 | [sql-repair-run-004-004.md](sql-repair-run-004-004.md) |
| 2026-07-10 | SQL Repair Experiment 005 | [sql-repair-run-004-005.md](sql-repair-run-004-005.md) |
| 2026-07-10 | SQL Repair Experiment 006 | [sql-repair-run-004-006.md](sql-repair-run-004-006.md) |
| 2026-07-10 | SFT V6 Error-Aware Planning | [sft-v6-error-aware.md](sft-v6-error-aware.md) |
| 2026-07-11 | LoRA Training Run 006 | [lora-training-run-006.md](lora-training-run-006.md) |
| 2026-07-11 | LoRA Run 006 Eval 010 | [eval-010-lora-run-006.md](eval-010-lora-run-006.md) |
| 2026-07-12 | Schema Guidance Quality 001 | [schema-guidance-quality-001.md](schema-guidance-quality-001.md) |
| 2026-07-12 | LoRA Training Run 007 | [lora-training-run-007.md](lora-training-run-007.md) |
| 2026-07-12 | LoRA Run 007 Eval 011 | [eval-011-lora-run-007.md](eval-011-lora-run-007.md) |
| 2026-07-13 | SFT V7 Source-Table Supervision | [sft-v7-source-table-supervision.md](sft-v7-source-table-supervision.md) |
| 2026-07-13 | LoRA Training Run 008 | [lora-training-run-008.md](lora-training-run-008.md) |
| 2026-07-13 | LoRA Run 008 Eval 012 | [eval-012-lora-run-008.md](eval-012-lora-run-008.md) |
| 2026-07-14 | Focused Repair Error Set 001 | [focused-repair-error-set-001.md](focused-repair-error-set-001.md) |
| 2026-07-14 | SQL Repair Experiment 007 | [sql-repair-unqualified-column-001.md](sql-repair-unqualified-column-001.md) |
| 2026-07-14 | SQL Repair Experiment 008 | [sql-repair-undeclared-alias-001.md](sql-repair-undeclared-alias-001.md) |
| 2026-07-14 | SQL Repair Experiment 009 | [sql-repair-unqualified-join-001.md](sql-repair-unqualified-join-001.md) |
| 2026-07-14 | SQL Repair Experiment 010 | [sql-repair-syntax-fragment-001.md](sql-repair-syntax-fragment-001.md) |
| 2026-07-14 | LoRA Training Run 009 | [lora-training-run-009.md](lora-training-run-009.md) |
| 2026-07-14 | LoRA Run 009 Eval 013 | [eval-013-lora-run-009.md](eval-013-lora-run-009.md) |
| 2026-07-14 | Run 009 Full Validation Eval 014 | [eval-014-lora-run-009-full-validation.md](eval-014-lora-run-009-full-validation.md) |
| 2026-07-14 | Model Capacity Decision 001 | [model-capacity-decision-001.md](model-capacity-decision-001.md) |
| 2026-07-14 | LoRA Training Run 010 | [lora-training-run-010.md](lora-training-run-010.md) |
| 2026-07-14 | Run 010 and Cascade Eval 015 | [eval-015-lora-run-010.md](eval-015-lora-run-010.md) |
| 2026-07-14 | Filtered BIRD Training Pivot | [filtered-bird-training-pivot.md](filtered-bird-training-pivot.md) |
| 2026-07-14 | Filtered BIRD Runs 011/012 Eval 016 | [eval-016-filtered-bird-training.md](eval-016-filtered-bird-training.md) |
| 2026-07-14 | Qwen 3B QLoRA Readiness and Length-Safety Correction | [qwen-3b-qlora-readiness.md](qwen-3b-qlora-readiness.md) |
| 2026-07-14 | Qwen 3B Run 013 Eval 017 | [eval-017-qwen-3b-run-013.md](eval-017-qwen-3b-run-013.md) |
| 2026-07-14 | Database Value Retrieval V1 | [value-retrieval-v1.md](value-retrieval-v1.md) |
| 2026-07-14 | SFT V10 Value-Context Alignment | [sft-v10-value-context.md](sft-v10-value-context.md) |
| 2026-07-14 | Consensus and Gold-Free SQL Judge Eval 018 | [eval-018-consensus-and-sql-judge.md](eval-018-consensus-and-sql-judge.md) |
| 2026-07-15 | Unseen BIRD Dev Questions Eval 019 | [eval-019-unseen-bird-dev.md](eval-019-unseen-bird-dev.md) |

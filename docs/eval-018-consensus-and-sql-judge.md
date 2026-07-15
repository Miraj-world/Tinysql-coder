# Eval 018: Consensus and Gold-Free SQL Judge

Date: 2026-07-14

## Results

| Configuration | Execution matches | SQL executed |
|---|---:|---:|
| Value-guided Run 013 + repair | 35/100 | 89/100 |
| Execution-only fallback cascade | 39/100 | 99/100 |
| Ten-source non-empty result consensus | 44/100 | 99/100 |
| Beam-2 Run 013 + repair | 35/100 | 93/100 |
| Gold-free semantic SQL judge | **46/100** | 95/100 |
| Semantic judge + repair | 45/100 | 98/100 |

The semantic judge is the final best configuration. It receives the question,
schema, evidence, up to eight executable candidate queries, their row counts,
and tiny result samples. It does not receive expected SQL or expected rows.

## Other Findings

- Run 014 value-context continuation plateaued after its step-25 checkpoint and
  scored 27/100 raw and 34/100 repaired, so it did not replace Run 013.
- Two-beam decoding added different candidates but did not improve consensus.
- Across the evaluated candidates, an analysis-only oracle could answer 60/100;
  this is not a deployable score, but confirms selection remains the bottleneck.
- Mechanical repair should not be applied after the judge because it reduced
  correctness from 46 to 45.

## Decision

Stop this experiment series at the user-requested final test. The verified best
score is 46/100, up from 35/100 at the start of the Qwen 3B improvement phase,
but it remains four points below the original 50/100 milestone.

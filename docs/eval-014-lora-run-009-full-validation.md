# Eval 014 - Run 009 Full Validation Benchmark

Date: 2026-07-14

## Goal

Evaluate Run 009 on all 100 held-out validation examples instead of relying
only on the fixed 20-question comparison sample.

One question changes a 20-example score by five percentage points. The
100-example benchmark provides a more stable estimate and a larger failure set
for designing the next training run.

## Evaluation Safety

The first execution attempt exposed a pathological generated query that kept
SQLite busy for several minutes. The evaluator and repair runner now interrupt
each individual query after five seconds and explicitly close SQLite
connections. This behavior has focused Windows tests.

Two gold queries also exceeded the five-second limit. They remain counted in
the 100-example headline so the benchmark denominator stays fixed, and are
reported separately below.

## Raw Run 009

```text
exact matches:                  4/100
execution matches:             22/100
predicted SQL that executed:   49/100
gold SQL that executed:        98/100
```

By difficulty:

| Difficulty | Execution matches | Predicted SQL that ran |
| --- | ---: | ---: |
| Simple | 10/30 | 20/30 |
| Moderate | 9/50 | 20/50 |
| Challenging | 3/20 | 9/20 |

## Run 009 Plus Repair

```text
exact matches:                  4/100
execution matches:             29/100
predicted SQL that executed:   75/100
gold SQL that executed:        98/100
```

By difficulty:

| Difficulty | Execution matches | Predicted SQL that ran |
| --- | ---: | ---: |
| Simple | 12/30 | 26/30 |
| Moderate | 13/50 | 35/50 |
| Challenging | 4/20 | 14/20 |

The repair stack added seven correct answers and made 26 additional queries
executable.

## Remaining Failure Distribution

| Category | Count |
| --- | ---: |
| Executes but returns wrong rows | 46 |
| Execution match | 29 |
| Invented column | 10 |
| Wrong table for column | 7 |
| Other execution error | 4 |
| Ambiguous or unqualified column | 3 |
| Hallucinated table | 1 |

The dominant problem is now semantic correctness. Forty-six queries run but
return the wrong answer. More syntax repair cannot solve that class reliably.

## Gold Timeouts

Q701 and Q518 exceeded the five-second safety limit even for the reference SQL.
The score over gold queries that completed is 29/98, but the fixed headline
remains 29/100.

## Lesson

The 20-question sample underestimated general performance: Run 009 + repair
scored 6/20 there but 29/100 on the full validation benchmark. The system is
learning useful SQL patterns, especially for simple and moderate questions,
but it is not yet strong on challenging multi-step semantics.

## Decision Needed for Run 010

The next path depends on the product constraint:

- Keep the 0.5B model and improve semantic training data, accepting a lower
  likely ceiling; or
- move to a larger base model such as the 1.5B Qwen coder and adapt the training
  pipeline to the 8 GB GPU.

A concrete success threshold should also be chosen. A reasonable next milestone
would be at least 50/100 execution matches after repair on this fixed benchmark.

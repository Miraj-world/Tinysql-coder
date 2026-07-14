# Eval 015 - Qwen 1.5B Run 010 and Cascade

Date: 2026-07-14

## Goal

Evaluate the Qwen2.5-Coder-1.5B adapter on the same fixed 100-question benchmark
as Run 009, then test a deterministic execution-fallback cascade.

The predeclared promising milestone was 50/100 execution matches after repair.

## Run 010 Raw Result

```text
exact matches:                  3/100
execution matches:             26/100
predicted SQL that executed:   62/100
gold SQL that executed:        98/100
```

Compared with the 0.5B Run 009 raw result:

```text
Run 009 raw: 22/100 correct, 49/100 executable
Run 010 raw: 26/100 correct, 62/100 executable
```

The larger model improved both raw correctness and executability.

## Run 010 Plus Repair

```text
exact matches:                  4/100
execution matches:             28/100
predicted SQL that executed:   74/100
```

This did not beat Run 009 plus repair at 29/100. Run 010 gained different
questions but lost some questions that Run 009 solved, showing that the two
adapters are complementary rather than one strictly replacing the other.

## Execution-Fallback Cascade

The cascade uses:

```text
primary:  Run 009 repaired SQL
fallback: Run 010 repaired SQL
rule:     use fallback only when primary SQL fails to execute
```

This rule uses no gold answer and does not inspect correctness. It relies only
on the safe runtime fact that SQLite rejected the primary query.

Result:

```text
fallbacks used:                25/100
exact matches:                  5/100
execution matches:             35/100
predicted SQL that executed:   92/100
gold SQL that executed:        98/100
```

The cascade is the best system result so far, improving from 29/100 to 35/100.

## Remaining Failures

| Category | Count |
| --- | ---: |
| Executes but returns wrong rows | 57 |
| Execution match | 35 |
| Wrong table for column | 5 |
| Ambiguous or unqualified column | 2 |
| Other execution error | 1 |

The system is now highly executable, but semantic correctness remains the main
problem. Fifty-seven queries run and return the wrong rows.

## Decision

The 1.5B pivot produced a better raw model and, through complementary fallback,
a better end-to-end system. However, it did not reach the 50/100 milestone and
is not yet dependable enough for unsupervised use.

The next improvement should add diverse, verified semantic training examples.
Repeating the same 400 unique questions for more steps is unlikely to close the
remaining 15-point gap. Future data should emphasize correct query plans,
aggregations, ranking, date logic, and multi-table filters drawn from the 57
executable wrong-result cases.

# Eval 013 - LoRA Run 009

Date: 2026-07-14

## Goal

Measure whether extending the clean V6 training recipe from 80 to 160 steps
improves SQL correctness on the same fixed 20-question evaluation set.

## Raw Result

```text
exact matches:                 2/20
execution matches:             5/20
predicted SQL that executed:   7/20
gold SQL that executed:       20/20
```

This is the best raw model result so far:

```text
Run 007 raw execution matches: 4/20
Run 009 raw execution matches: 5/20
```

Compared with Run 007, Run 009 gained correct answers Q212 and Q736, but lost
Q1526. Its five raw execution matches were:

```text
Q212
Q555
Q733
Q736
Q1394
```

## Repair Result

The complete conservative repair stack produced:

```text
exact matches:                 2/20
execution matches:             6/20
predicted SQL that executed:  13/20
```

Compared with Run 007 + repair, Run 009 + repair gained Q212 but lost Q1526,
leaving both systems at 6/20. Run 004 + repair remains the best overall system
at 7/20.

## Lesson

Longer training improved the model itself. Lower validation loss corresponded
to one additional held-out execution match, so Run 007 was somewhat
undertrained at 80 steps.

However, the gain was not uniform. Run 009 forgot one previously correct hard
example, and its repaired score did not exceed Run 004. The next training
improvement should preserve the best checkpoint during training and stop based
on validation behavior instead of saving only the final requested step.

## Follow-up

This 20-question comparison remains useful for continuity with earlier runs,
but it is no longer the primary headline. The later full validation benchmark
measured Run 009 at 22/100 raw execution matches and 29/100 after repair. See
[Eval 014](eval-014-lora-run-009-full-validation.md).

# SFT V10: Value-Context Alignment

Date: 2026-07-14

## Why

Inference-time value retrieval improved Run 013 from 34/100 to 35/100 after
repair. Combining the value-guided model with execution-only fallbacks raised
the project best from 36/100 to 39/100, with 99/100 predictions executable.

The Run 013 adapter was not trained to interpret a `Relevant database values`
section. V10 aligns training with that inference format using the official BIRD
training column descriptions and example values.

## Leakage Guards

- source: 6,601 filtered BIRD training rows;
- 62 training databases and 7 entirely separate validation databases;
- zero database overlap between training and validation;
- zero exact question overlap with mini-dev;
- at most eight question-relevant column descriptions per prompt;
- mini-dev expected SQL is never read during data preparation.

## Smoke Test

```text
initial adapter:                 Run 013 step 350
raw training examples:          5,825
safe training examples:         5,442
validation examples retained:     776/776
steps:                              5
validation loss:                 0.1574
peak CUDA allocated:             6.637 GB
automated tests:                 48 passed
```

The smoke test proves that a QLoRA continuation fits the local 8 GB GPU. The
next experiment is Run 014, a lower-learning-rate continuation on V10 followed
by the unchanged 100-question execution benchmark.

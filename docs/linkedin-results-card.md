# TinySQL-coder: Evaluation Progress

## From 22% to 29% correct - and from 49% to 75% executable

| Evaluation stage | Correct SQL | Executable SQL |
| --- | ---: | ---: |
| Run 009 - raw model | 22/100 | 49/100 |
| Run 009 - after guarded repair | **29/100** | **75/100** |
| Improvement | **+7** | **+26** |

> Making SQL executable was easier than making it semantically correct.

The remaining challenge is no longer just SQL syntax. Of the 100 repaired
predictions, 46 executed successfully but returned the wrong rows.

**Stack:** Qwen2.5-Coder | LoRA | BIRD text-to-SQL | SQLite execution evaluation

# TinySQL-coder

TinySQL-coder is a learning-first text-to-SQL fine-tuning project using the
BIRD mini-dev dataset.

Important clarification: **BIRD does not mean bird images here**. BIRD is a
database question-answering benchmark. Each example contains a natural-language
question, database context, and the SQL query that answers the question.

The project goal is:

```text
database schema + question + evidence -> SQL query
```

## Current Status

Done so far:

1. Downloaded and inspected the BIRD mini-dev dataset.
2. Added the matching official SQLite database package locally.
3. Extracted compact schema text from each SQLite database.
4. Built processed JSONL training data with schema, question, evidence, and gold SQL.
5. Split data into train and validation sets.
6. Built a fixed 20-example baseline evaluation set.
7. Ran base Qwen baseline evaluation.
8. Added execution-based SQL evaluation against real SQLite databases.
9. Prepared chat-style supervised fine-tuning data.
10. Set up CUDA-enabled PyTorch.
11. Ran a LoRA smoke test.
12. Ran LoRA Training Run 001.
13. Evaluated Qwen + LoRA Run 001.
14. Added a comparison tool for base-vs-LoRA evaluation reports.
15. Added failure-pattern analysis for SQL execution errors.
16. Created SFT V2 with schema guidance and ran LoRA Run 002.
17. Created SFT V3 to oversample join-heavy examples for Run 003.
18. Ran LoRA Run 003 and got the first fine-tuned execution improvement.
19. Inspected Run 003's successful predictions to understand what improved.
20. Created SFT V4 to focus on harder join and subquery examples for Run 004.
21. Ran LoRA Run 004 and reached the best execution score so far.

Latest high-level result:

```text
Base Qwen execution matches:    1/20
LoRA Run 001 execution matches: 0/20
LoRA Run 002 execution matches: 0/20
LoRA Run 003 execution matches: 2/20
LoRA Run 004 execution matches: 3/20
```

The training pipeline works, but the first short LoRA run did not improve SQL
execution accuracy yet. The main failure pattern is still schema grounding:
the model often puts a real column on the wrong table or skips a needed join.

## Project Structure

```text
.
+-- data/                         local only, ignored by Git
|   +-- bird_mini_dev/
|       +-- raw/
|       +-- dev_databases/
|       +-- schema/
|       +-- processed/
|       +-- sft/
+-- docs/                         experiment journals and notes
+-- models/                       local only, ignored by Git
|   +-- huggingface/
|   +-- lora-smoke-test/
|   +-- tinysql-coder-lora-run-001/
+-- notebooks/
|   +-- 001-data-exploration.ipynb
|   +-- 002-inspect-qwen-model.ipynb
+-- outputs/                      generated eval outputs, ignored by Git
+-- scripts/
|   +-- download-dataset.py
|   +-- extract_schema_text.py
|   +-- prepare_training_data.py
|   +-- split_training_data.py
|   +-- prepare_sft_data.py
|   +-- prepare_sft_data_v2.py
|   +-- prepare_sft_data_v3.py
|   +-- prepare_sft_data_v4.py
|   +-- create_baseline_eval_set.py
|   +-- run_baseline_model.py
|   +-- evaluate_sql_execution.py
|   +-- compare_eval_runs.py
|   +-- analyze_failure_patterns.py
|   +-- check_training_readiness.py
|   +-- train_lora_smoke_test.py
|   +-- train_lora.py
+-- requirements.txt
+-- README.md
```

The `data/`, `models/`, and `outputs/` folders are intentionally ignored by
Git. They contain downloaded datasets, generated files, model weights, adapters,
and evaluation outputs.

## Environment

Use the project-local Python 3.12 environment:

```text
.venv312
```

In VS Code notebooks, select:

```text
Finetuning Model (Python 3.12)
```

Install dependencies:

```powershell
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt
```

The current setup uses CUDA-enabled PyTorch:

```text
torch: 2.11.0+cu128
CUDA available: True
GPU: NVIDIA GeForce RTX 4070 Laptop GPU
```

## Data Pipeline

Download the mini-dev dataset:

```powershell
.\.venv312\Scripts\python.exe scripts\download-dataset.py
```

Extract SQLite schemas into compact text:

```powershell
.\.venv312\Scripts\python.exe scripts\extract_schema_text.py
```

Prepare processed training data:

```powershell
.\.venv312\Scripts\python.exe scripts\prepare_training_data.py
```

Inspect processed examples:

```powershell
.\.venv312\Scripts\python.exe scripts\inspect_training_data.py
```

Split train/validation:

```powershell
.\.venv312\Scripts\python.exe scripts\split_training_data.py
```

Prepare chat-style SFT data:

```powershell
.\.venv312\Scripts\python.exe scripts\prepare_sft_data.py
```

Current data counts:

```text
Raw examples: 500
Train examples: 400
Validation examples: 100
SFT train examples: 400
SFT validation examples: 100
```

## Schema Format

The schema extraction step turns each SQLite database into compact table/column
text like:

```text
atom(molecule_id, atom_id, element)
bond(molecule_id, bond_id, bond_type)
connected(atom_id, atom_id2, bond_id)
molecule(molecule_id, label)
```

Plain English: each line is one database table, and the names inside
parentheses are that table's columns.

## Baseline Evaluation

Create the fixed baseline evaluation set:

```powershell
.\.venv312\Scripts\python.exe scripts\create_baseline_eval_set.py
```

Run the base Qwen model:

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py
```

Run only a small smoke test:

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py --limit 2
```

Evaluate SQL by execution:

```powershell
.\.venv312\Scripts\python.exe scripts\evaluate_sql_execution.py
```

Latest base model execution result:

```text
Exact matches: 0/20
Execution matches: 1/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 2/20
```

Execution match is more useful than exact string match because two different
SQL queries can return the same correct result.

## LoRA Fine-Tuning

We are fine-tuning Qwen with LoRA adapters.

Base model:

```text
Qwen/Qwen2.5-Coder-0.5B-Instruct
```

LoRA means we freeze the original Qwen weights and train a small adapter on top.
We are still using Qwen; LoRA is the fine-tuning method.

Run the training readiness check:

```powershell
.\.venv312\Scripts\python.exe scripts\check_training_readiness.py
```

Run the tiny smoke test:

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora_smoke_test.py
```

Run the first real LoRA trainer:

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py --max-steps 20 --gradient-accumulation-steps 4 --eval-every 5 --validation-limit 10 --output-dir models\tinysql-coder-lora-run-001
```

The trainer can also accept alternate SFT files:

```powershell
.\.venv312\Scripts\python.exe scripts\train_lora.py --train-path data\bird_mini_dev\sft_v2\train_sft_v2.jsonl --validation-path data\bird_mini_dev\sft_v2\validation_sft_v2.jsonl --max-sequence-length 3072 --output-dir models\tinysql-coder-lora-run-002
```

LoRA Run 001 result:

```text
trainable params: 4,399,104
all params: 498,431,872
trainable percent: 0.8826
final validation loss: 0.3360
```

The adapter is saved locally under:

```text
models/tinysql-coder-lora-run-001
```

## Evaluate A LoRA Adapter

Generate predictions with the LoRA adapter:

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py --adapter-path models\tinysql-coder-lora-run-001 --output-path outputs\lora-run-001\predictions.jsonl
```

Evaluate those predictions by execution:

```powershell
.\.venv312\Scripts\python.exe scripts\evaluate_sql_execution.py --predictions-path outputs\lora-run-001\predictions.jsonl --output-path outputs\lora-run-001\execution_eval.jsonl --summary-path outputs\lora-run-001\execution_eval_summary.json
```

LoRA Run 001 execution result:

```text
Exact matches: 0/20
Execution matches: 0/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 2/20
```

This means the adapter trained successfully, but did not improve SQL quality in
the first short run.

## Compare Runs

Generate a local markdown comparison report:

```powershell
.\.venv312\Scripts\python.exe scripts\compare_eval_runs.py
```

Default comparison:

```text
outputs/baseline/execution_eval.jsonl
vs
outputs/lora-run-001/execution_eval.jsonl
```

Default generated report:

```text
outputs/comparisons/base-vs-lora-run-001.md
```

This output report is ignored by Git.

## Analyze Failure Patterns

Run failure analysis on a SQL execution-evaluation file:

```powershell
.\.venv312\Scripts\python.exe scripts\analyze_failure_patterns.py
```

Default input:

```text
outputs/lora-run-001/execution_eval.jsonl
```

Default generated report:

```text
outputs/analysis/lora-run-001-failure-analysis.md
```

Latest LoRA Run 001 failure pattern:

```text
wrong_table_for_column: 13
ambiguous_or_unqualified_column: 2
executes_wrong_result: 2
hallucinated_table: 2
execution_error_other: 1
```

Mentor translation: the model is often choosing relevant column names but
placing them on the wrong table. Run 002 should teach table-column ownership and
join paths more explicitly.

LoRA Run 002 reduced `wrong_table_for_column` failures from 13 to 11, but still
scored 0/20 execution matches. The next likely improvement is not only clearer
schema text; it may require more targeted join-focused training examples.

LoRA Run 003 used join-focused oversampling and improved to 2/20 execution
matches, with 4/20 predicted SQL queries executing successfully.

The two Run 003 execution matches were a single-table aggregate and a simple
two-table join. That suggests join-focused training helped on simpler join
structures, while moderate/challenging joins still need stronger supervision.

LoRA Run 004 used hard-join oversampling and improved to 3/20 execution
matches. The added success was another simple two-table join, so the next
frontier is still moderate/challenging join reasoning.

## Notebooks

Dataset exploration:

```text
notebooks/001-data-exploration.ipynb
```

Model file and LoRA target-module inspection:

```text
notebooks/002-inspect-qwen-model.ipynb
```

Use the second notebook to see where Qwen layer names like `q_proj`,
`v_proj`, `gate_proj`, and `down_proj` come from.

## Evaluation Journal

Experiment notes are in:

```text
docs/evaluation-journal.md
```

Each major check or evaluation has its own markdown file under `docs/`.

Important entries:

```text
docs/eval-001-baseline.md
docs/eval-004-schema-grounding-prompt.md
docs/lora-training-run-001.md
docs/eval-005-lora-run-001.md
docs/eval-comparison-tool.md
docs/failure-pattern-analysis-001.md
docs/sft-v2-schema-guidance.md
```

## Next Step

The next useful project step is not to blindly train longer.

First inspect the comparison report and identify the most common failure
pattern. Current evidence points to schema grounding:

```text
wrong table for a column
missing join
invented plausible column
```

Then improve either the SFT format or training examples so the model learns
table-column ownership more explicitly before running LoRA Training Run 002.

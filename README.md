# Fine-Tuning A Text-to-SQL Model

This project is a learning-first fine-tuning project using the BIRD mini-dev dataset.

Important clarification: this dataset does not contain bird images. **BIRD** here refers to a text-to-SQL benchmark dataset. Each example contains a natural-language database question and the SQL query that answers it.

The current goal is to build the data preparation foundation before training a model.

## Current Status

Done so far:

1. Created the project structure.
2. Downloaded the BIRD mini-dev dataset.
3. Confirmed the raw data is stored as an Arrow dataset file.
4. Created a notebook to inspect the raw dataset.
5. Converted the raw dataset into JSONL training examples.
6. Added a script to inspect the generated training examples.
7. Split the examples into training and validation sets.

Current dataset size:

```text
Raw examples: 500
Training examples: 400
Validation examples: 100
```

Difficulty distribution after splitting:

```text
Train:
  challenging: 82
  moderate: 200
  simple: 118

Validation:
  challenging: 20
  moderate: 50
  simple: 30
```

## Project Structure

```text
.
+-- data/
|   +-- bird_mini_dev/
|       +-- raw/
|       |   +-- bird-original.arrow
|       |   +-- dataset_info.json
|       |   +-- state.json
|       +-- processed/
|           +-- training_data.jsonl
|           +-- train.jsonl
|           +-- validation.jsonl
+-- models/
+-- notebooks/
|   +-- 001-data-exploration.ipynb
+-- outputs/
+-- scripts/
|   +-- download-dataset.py
|   +-- prepare_training_data.py
|   +-- inspect_training_data.py
|   +-- split_training_data.py
+-- requirements.txt
+-- README.md
```

## Python Environment

The notebook originally failed because the selected Python kernel did not have the `datasets` package installed. A project-local Python 3.12 environment was created:

```text
.venv312
```

In VS Code, select this notebook kernel:

```text
Finetuning Model (Python 3.12)
```

To run scripts from the terminal:

```powershell
.\.venv312\Scripts\python.exe scripts\prepare_training_data.py
```

## Raw Dataset

The raw dataset file is:

```text
data/bird_mini_dev/raw/bird-original.arrow
```

It contains 500 examples with these columns:

```text
question_id
db_id
question
evidence
SQL
difficulty
```

Meaning of the important columns:

```text
question     = natural-language database question
evidence     = extra hint or rule needed to answer the question
SQL          = target SQL query
difficulty   = simple, moderate, or challenging
db_id        = database identifier
```

## Notebook

The notebook is:

```text
notebooks/001-data-exploration.ipynb
```

It loads the Arrow file and displays the first records in a readable table.

Use it to understand the raw data before training anything.

## Data Preparation

The preparation script is:

```text
scripts/prepare_training_data.py
```

It converts each raw dataset row into a training example shaped like this:

```json
{
  "instruction": "Convert the database question into a valid SQL query.",
  "input": "Database ID: ...\nSchema:\n...\nQuestion: ...\nEvidence: ...",
  "output": "SELECT ...",
  "metadata": {
    "question_id": 1471,
    "db_id": "...",
    "difficulty": "simple"
  }
}
```

Generated file:

```text
data/bird_mini_dev/processed/training_data.jsonl
```

JSONL means JSON Lines. Each line is one complete training example.

Run it with:

```powershell
.\.venv312\Scripts\python.exe scripts\prepare_training_data.py
```

## Training Data Inspection

The inspection script is:

```text
scripts/inspect_training_data.py
```

It checks:

```text
total number of examples
missing instruction fields
missing input fields
missing output fields
difficulty distribution
first 5 readable examples
```

Run it with:

```powershell
.\.venv312\Scripts\python.exe scripts\inspect_training_data.py
```

Latest inspection result:

```text
Total examples: 500

Missing fields:
  instruction: 0
  input: 0
  output: 0

Difficulty counts:
  challenging: 102
  moderate: 250
  simple: 148
```

## Train And Validation Split

The split script is:

```text
scripts/split_training_data.py
```

It splits the full processed dataset into:

```text
data/bird_mini_dev/processed/train.jsonl
data/bird_mini_dev/processed/validation.jsonl
```

The validation ratio is:

```python
VALIDATION_RATIO = 0.2
```

That means:

```text
80% training
20% validation
```

For this dataset:

```text
500 total examples
400 train examples
100 validation examples
```

The split is stratified by `difficulty`, which means the script tries to preserve a similar mix of simple, moderate, and challenging examples in both train and validation.

Run it with:

```powershell
.\.venv312\Scripts\python.exe scripts\split_training_data.py
```

## What The Model Will Learn

The task is:

```text
instruction + input -> SQL
```

Example:

```text
Instruction:
Convert the database question into a valid SQL query.

Input:
Database ID: debit_card_specializing
Question: What is the ratio of customers who pay in EUR against customers who pay in CZK?
Evidence: ratio = count(EUR) / count(CZK)

Output:
SELECT ...
```

This is a text generation task, not an image classification task.

## Important Mentor Notes

The current format is good for a first baseline.

However, serious text-to-SQL models usually need database schema context: table names, column names, column types, and relationships. Right now the training input includes only:

```text
database ID
question
evidence
```

It does not yet include the actual database schema. That is acceptable for the first learning pass, but schema context will likely become important later.

## Reproduce The Current Data Pipeline

From the project root:

```powershell
.\.venv312\Scripts\python.exe scripts\prepare_training_data.py
.\.venv312\Scripts\python.exe scripts\inspect_training_data.py
.\.venv312\Scripts\python.exe scripts\split_training_data.py
```

Expected final files:

```text
data/bird_mini_dev/processed/training_data.jsonl
data/bird_mini_dev/processed/train.jsonl
data/bird_mini_dev/processed/validation.jsonl
```

The `data/`, `models/`, and `outputs/` folders are intentionally ignored by Git. They can contain downloaded datasets, generated training files, model artifacts, and evaluation outputs. Recreate the data files locally with the scripts above instead of committing them.

## Baseline Evaluation Set

The baseline evaluation set script is:

```text
scripts/create_baseline_eval_set.py
```

It creates a small, balanced sample from `validation.jsonl` so the same examples can be used before and after fine-tuning.

Generated local file:

```text
outputs/baseline/baseline_eval_set.jsonl
```

This file is intentionally ignored by Git because `outputs/` is for local generated artifacts.

Run it with:

```powershell
.\.venv312\Scripts\python.exe scripts\create_baseline_eval_set.py
```

Latest baseline sample:

```text
Baseline sample size: 20
challenging: 7
moderate: 7
simple: 6
```

## Next Step

The baseline model runner is:

```text
scripts/run_baseline_model.py
```

It loads `outputs/baseline/baseline_eval_set.jsonl`, sends each prompt to a base model, and saves predictions to:

```text
outputs/baseline/baseline_predictions.jsonl
```

Default model:

```text
Qwen/Qwen2.5-Coder-0.5B-Instruct
```

Run a small smoke test first:

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py --limit 2
```

Then run all 20 baseline examples:

```powershell
.\.venv312\Scripts\python.exe scripts\run_baseline_model.py
```

This gives us a before-fine-tuning result to compare against later.

Note: the current local PyTorch install is CPU-only. That is fine for a small baseline smoke test, but actual fine-tuning should use a CUDA-enabled PyTorch install.

Model downloads are cached inside the project under:

```text
models/huggingface
```

The `models/` folder is ignored by Git, so downloaded base models and future fine-tuned artifacts stay local and are not pushed to GitHub.

Latest schema-informed baseline run:

```text
Model: Qwen/Qwen2.5-Coder-0.5B-Instruct
Device: CPU
Examples: 20
Exact matches: 0/20
```

Exact string match is a very strict metric for SQL because two different SQL strings can sometimes be logically equivalent. The schema-informed run still scored 0/20 exact match, but the predictions used more real table and column names. The next improvement should be execution-based evaluation, where generated SQL and gold SQL are run against the same SQLite database and their returned results are compared.

Evaluation notes and failure analysis are documented in:

```text
docs/evaluation-journal.md
```

The execution evaluator is:

```text
scripts/evaluate_sql_execution.py
```

It runs gold SQL and predicted SQL against the matching SQLite database and compares returned rows.

Latest execution evaluation:

```text
Exact matches: 0/20
Execution matches: 1/20
Gold SQL executed successfully: 20/20
Predicted SQL executed successfully: 2/20
```

## Schema Availability Check

The schema availability script is:

```text
scripts/inspect_schema_availability.py
```

It checks whether the expected BIRD database folders are available locally under:

```text
data/bird_mini_dev/dev_databases
```

Run it with:

```powershell
.\.venv312\Scripts\python.exe scripts\inspect_schema_availability.py
```

Current status: the official package has been downloaded locally, and all 11 expected database folders are present under `data/bird_mini_dev/dev_databases`.

## Schema Text Extraction

The schema extraction script is:

```text
scripts/extract_schema_text.py
```

It reads each local `.sqlite` database and writes compact table/column schema text to:

```text
data/bird_mini_dev/schema/schema_text.json
```

Example schema format:

```text
atom(molecule_id, atom_id, element)
bond(molecule_id, bond_id, bond_type)
connected(atom_id, atom_id2, bond_id)
molecule(molecule_id, label)
```

Run it with:

```powershell
.\.venv312\Scripts\python.exe scripts\extract_schema_text.py
```

Latest result:

```text
Extracted schemas: 11
```

Next step: inject this schema text into each training example and regenerate `training_data.jsonl`, `train.jsonl`, `validation.jsonl`, and the baseline evaluation set.

## SFT Data Preparation

The supervised fine-tuning data script is:

```text
scripts/prepare_sft_data.py
```

It converts processed examples into chat-style training records:

```text
system message -> model behavior
user message -> instruction, schema, question, evidence
assistant message -> gold SQL
```

Generated local files:

```text
data/bird_mini_dev/sft/train_sft.jsonl
data/bird_mini_dev/sft/validation_sft.jsonl
```

Latest result:

```text
Train SFT examples: 400
Validation SFT examples: 100
```

These files are ignored by Git because they live under `data/`.

## Training Readiness

The training readiness script is:

```text
scripts/check_training_readiness.py
```

It checks SFT files, tokenizer compatibility, token lengths, and CUDA availability.

Latest result:

```text
Train SFT examples: 400
Validation SFT examples: 100
CUDA available: True
GPU: NVIDIA GeForce RTX 4070 Laptop GPU
Max token length: 1198
Recommended max sequence length: 2048
```

CUDA-enabled PyTorch is installed in `.venv312` using the CUDA 12.8 wheel build. The next step is to create a small LoRA/SFT training smoke test before running a longer fine-tuning job.

## LoRA Training Smoke Test

The LoRA smoke-test script is:

```text
scripts/train_lora_smoke_test.py
```

It trains only a few examples for two steps. The goal is not model quality; the goal is to prove the GPU training loop works.

Latest result:

```text
GPU: NVIDIA GeForce RTX 4070 Laptop GPU
trainable params: 4,399,104
step 1/2 loss: 1.8960
step 2/2 loss: 1.7379
```

Saved local adapter:

```text
models/lora-smoke-test
```

The adapter is ignored by Git because it lives under `models/`.

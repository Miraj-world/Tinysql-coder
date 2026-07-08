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
  "input": "Database ID: ...\nQuestion: ...\nEvidence: ...",
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

## Next Step

The next project step is to create a baseline evaluation before fine-tuning.

Why:

```text
Before training, measure how well an existing model performs.
After training, compare against that baseline.
```

This prevents us from training blindly.

The next script will likely:

```text
1. Load a small sample from validation.jsonl.
2. Send each question to a baseline model.
3. Collect generated SQL.
4. Compare generated SQL against the expected SQL.
5. Save results under outputs/.
```

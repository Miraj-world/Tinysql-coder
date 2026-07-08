# Evaluation Journal

This journal records model evaluation results, failures, lessons, and next steps. Raw generated artifacts live under `outputs/`; this file is for human interpretation.

## 2026-07-08 - Baseline Eval 001

### Goal

Run a base model on a fixed 20-example validation sample before fine-tuning.

The purpose of this run was to establish a starting point. Later, after fine-tuning or prompt improvements, we can compare against this baseline.

### Model

```text
Qwen/Qwen2.5-Coder-0.5B-Instruct
```

### Runtime

```text
Device: CPU
Examples: 20
```

Note: the machine has an NVIDIA GPU, but the current PyTorch install is CPU-only. That is acceptable for a small baseline run, but actual fine-tuning should use a CUDA-enabled PyTorch install.

### Dataset

Source dataset:

```text
BIRD mini-dev
```

Evaluation sample:

```text
outputs/baseline/baseline_eval_set.jsonl
```

Predictions:

```text
outputs/baseline/baseline_predictions.jsonl
```

Sample difficulty mix:

```text
challenging: 7
moderate: 7
simple: 6
```

### Result

```text
Exact match: 0/20
```

### What Failed

The model generated SQL for every prompt, but none of the generated queries exactly matched the expected SQL.

Common failure pattern:

```text
The model guessed table names and column names.
```

For example, it often wrote plausible-looking SQL using tables that were not necessarily the correct tables from the target database.

### Why It Failed

The current prompt includes:

```text
database ID
question
evidence
```

The prompt does not include:

```text
table names
column names
foreign keys
schema relationships
column meanings
```

For text-to-SQL, this is a major missing piece. A model cannot reliably generate correct SQL if it does not know the database schema.

### Metric Limitation

Exact string match is strict.

Two SQL queries can sometimes be logically equivalent while using different formatting, aliases, or expression order. So `0/20 exact match` does not automatically mean every answer is completely useless.

However, the failures are still meaningful because many predictions appear schema-incorrect, not just formatting-different.

### Lesson

Text-to-SQL is not only a language-generation problem. It is also a schema-grounding problem.

The model needs database structure in the prompt or training example. Without schema context, it is forced to guess.

### Decision

Before fine-tuning, improve the data format.

The next version of the training examples and baseline prompts should include schema context.

### Next Step

Add database schema context to each example.

Target prompt shape:

```text
Instruction:
Convert the database question into a valid SQL query.

Database ID:
...

Schema:
table_1(column_a, column_b, ...)
table_2(column_c, column_d, ...)

Question:
...

Evidence:
...

Return only the SQL query.
```

After that:

```text
1. Regenerate training_data.jsonl.
2. Regenerate train.jsonl and validation.jsonl.
3. Regenerate the baseline eval set.
4. Rerun the base model baseline.
5. Compare the new result against 0/20 exact match.
```

## 2026-07-08 - Schema Availability Check

### Goal

Check whether the local project already has the BIRD database folders needed to add schema context.

### Result

The row dataset is present, but the database/schema folders are missing.

Expected local folder:

```text
data/bird_mini_dev/dev_databases
```

Missing databases:

```text
california_schools
card_games
codebase_community
debit_card_specializing
european_football_2
financial
formula_1
student_club
superhero
thrombosis_prediction
toxicology
```

### Why This Matters

The baseline failed partly because the model did not know the schema. To add schema context, the project needs the official BIRD Mini-Dev database folders, especially the `database_description` files and/or SQLite database files.

### Next Step

Download the official BIRD Mini-Dev complete package and place its `dev_databases` folder at:

```text
data/bird_mini_dev/dev_databases
```

## 2026-07-08 - Database Package Added

### Goal

Download the official BIRD Mini-Dev complete package and add the missing local database folders.

### Result

The package was downloaded from the official BIRD Mini-Dev Google Drive link referenced by the BIRD repository. It was extracted locally, and the `dev_databases` folder was copied into:

```text
data/bird_mini_dev/dev_databases
```

### Verification

The schema availability script now finds all 11 expected databases:

```text
california_schools
card_games
codebase_community
debit_card_specializing
european_football_2
financial
formula_1
student_club
superhero
thrombosis_prediction
toxicology
```

Each database folder includes a SQLite database file and a `database_description` folder.

Example:

```text
data/bird_mini_dev/dev_databases/toxicology/
  toxicology.sqlite
  database_description/
    atom.csv
    bond.csv
    connected.csv
    molecule.csv
```

### Next Step

Extract compact schema text from each SQLite database so prompts can include table and column names.

## 2026-07-08 - Schema Text Extraction

### Goal

Create compact schema text for each BIRD Mini-Dev database.

### Script

```text
scripts/extract_schema_text.py
```

### Output

```text
data/bird_mini_dev/schema/schema_text.json
```

### Result

The script successfully extracted schema text for all 11 databases.

Example format:

```text
atom(molecule_id, atom_id, element)
bond(molecule_id, bond_id, bond_type)
connected(atom_id, atom_id2, bond_id)
molecule(molecule_id, label)
```

### Why This Matters

The previous baseline prompted the model with only database ID, question, and evidence. The extracted schema text gives the model table and column names, which should reduce schema guessing.

### Next Step

Inject schema text into the training data and baseline prompts.

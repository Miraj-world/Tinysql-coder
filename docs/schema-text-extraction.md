# Schema Text Extraction

Date: 2026-07-08

## Goal

Create compact schema text for each BIRD Mini-Dev database.

## Script

```text
scripts/extract_schema_text.py
```

## Output

```text
data/bird_mini_dev/schema/schema_text.json
```

## Result

The script successfully extracted schema text for all 11 databases.

Example format:

```text
atom(molecule_id, atom_id, element)
bond(molecule_id, bond_id, bond_type)
connected(atom_id, atom_id2, bond_id)
molecule(molecule_id, label)
```

## Why This Matters

The previous baseline prompted the model with only database ID, question, and evidence. The extracted schema text gives the model table and column names, which should reduce schema guessing.

## Next Step

Inject schema text into the training data and baseline prompts.

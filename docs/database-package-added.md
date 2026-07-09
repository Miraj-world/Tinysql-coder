# Database Package Added

Date: 2026-07-08

## Goal

Download the official BIRD Mini-Dev complete package and add the missing local database folders.

## Result

The package was downloaded from the official BIRD Mini-Dev Google Drive link referenced by the BIRD repository. It was extracted locally, and the `dev_databases` folder was copied into:

```text
data/bird_mini_dev/dev_databases
```

## Verification

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

## Next Step

Extract compact schema text from each SQLite database so prompts can include table and column names.

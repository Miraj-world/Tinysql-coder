# Schema Availability Check

Date: 2026-07-08

## Goal

Check whether the local project already has the BIRD database folders needed to add schema context.

## Result

The row dataset was present, but the database/schema folders were missing.

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

## Why This Matters

The baseline failed partly because the model did not know the schema. To add schema context, the project needs the official BIRD Mini-Dev database folders, especially the `database_description` files and/or SQLite database files.

## Next Step

Download the official BIRD Mini-Dev complete package and place its `dev_databases` folder at:

```text
data/bird_mini_dev/dev_databases
```

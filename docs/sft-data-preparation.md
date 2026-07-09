# SFT Data Preparation

Date: 2026-07-09

## Goal

Prepare the dataset for supervised fine-tuning.

## Why

The model will not train directly on our earlier `instruction`, `input`, and `output` fields. For a chat/code model, it is cleaner to train on message-style examples:

```text
system message
user message
assistant message
```

This teaches the model:

```text
When the user provides schema, question, and evidence, respond with SQL.
```

## Script

```text
scripts/prepare_sft_data.py
```

## Inputs

```text
data/bird_mini_dev/processed/train.jsonl
data/bird_mini_dev/processed/validation.jsonl
```

## Outputs

```text
data/bird_mini_dev/sft/train_sft.jsonl
data/bird_mini_dev/sft/validation_sft.jsonl
```

## Result

```text
Train SFT examples: 400
Validation SFT examples: 100
```

## Example Shape

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a careful text-to-SQL assistant. Use only the provided schema. Return only the SQL query."
    },
    {
      "role": "user",
      "content": "Instruction + schema-grounding rules + database ID + schema + question + evidence"
    },
    {
      "role": "assistant",
      "content": "SELECT ..."
    }
  ],
  "metadata": {
    "question_id": 1471,
    "db_id": "debit_card_specializing",
    "difficulty": "simple"
  }
}
```

## Lesson

This is the first dataset format that looks like actual fine-tuning input.

The earlier files helped us inspect and evaluate. The SFT files are what a training script can consume.

## Next Step

Create a small training script or training plan for the first fine-tuning run.

Before running full training, confirm:

```text
1. CUDA/GPU setup
2. model choice
3. LoRA/QLoRA strategy
4. max sequence length
5. output model/adapters path
```

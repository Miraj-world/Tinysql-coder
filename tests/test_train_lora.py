import unittest

from scripts.train_lora import tokenize_dataset


class CharacterTokenizer:
    pad_token_id = 0

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        text = "|".join(
            f"{message['role']}:{message['content']}" for message in messages
        )
        if add_generation_prompt:
            text += "|assistant:"
        return text

    def __call__(self, text, add_special_tokens=False, max_length=None, truncation=False):
        token_ids = list(range(len(text)))
        if truncation and max_length is not None:
            token_ids = token_ids[:max_length]
        return {"input_ids": token_ids, "attention_mask": [1] * len(token_ids)}


def example(prompt: str, answer: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": "sql"},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ]
    }


class OverlengthFilteringTests(unittest.TestCase):
    def test_drops_whole_overlength_example_when_requested(self):
        tokenizer = CharacterTokenizer()
        examples = [example("short", "SELECT 1"), example("x" * 100, "SELECT 2")]

        tokenized = tokenize_dataset(tokenizer, examples, 80, drop_overlength=True)

        self.assertEqual(len(tokenized), 1)
        self.assertTrue(any(label != -100 for label in tokenized[0]["labels"]))

    def test_default_path_keeps_truncatable_example_for_backward_compatibility(self):
        tokenizer = CharacterTokenizer()
        examples = [example("x" * 100, "SELECT 2")]

        tokenized = tokenize_dataset(tokenizer, examples, 40, drop_overlength=False)

        self.assertEqual(tokenized, [])


if __name__ == "__main__":
    unittest.main()

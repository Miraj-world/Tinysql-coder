import sys
import unittest
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_baseline_eval_set import (
    build_direct_guided_prompt,
    build_direct_join_prompt,
    build_direct_sql_prompt,
    choose_balanced_sample,
)


def example(question_id: int, difficulty: str) -> dict:
    return {"metadata": {"question_id": question_id, "difficulty": difficulty}}


class BalancedEvalSampleTests(unittest.TestCase):
    def setUp(self):
        self.examples = [
            *[example(index, "simple") for index in range(5)],
            *[example(index + 10, "moderate") for index in range(5)],
            *[example(index + 20, "challenging") for index in range(5)],
        ]

    def test_uses_requested_sample_size(self):
        sample = choose_balanced_sample(self.examples, sample_size=9)

        self.assertEqual(len(sample), 9)
        self.assertEqual(
            Counter(item["metadata"]["difficulty"] for item in sample),
            {"simple": 3, "moderate": 3, "challenging": 3},
        )

    def test_returns_all_examples_when_request_exceeds_available_rows(self):
        sample = choose_balanced_sample(self.examples, sample_size=100)

        self.assertEqual(len(sample), len(self.examples))
        self.assertEqual(
            {item["metadata"]["question_id"] for item in sample},
            {item["metadata"]["question_id"] for item in self.examples},
        )

    def test_sampling_is_deterministic(self):
        first = choose_balanced_sample(self.examples, sample_size=7)
        second = choose_balanced_sample(self.examples, sample_size=7)

        self.assertEqual(first, second)


class DirectSqlPromptTests(unittest.TestCase):
    def test_prompt_has_no_planning_scaffolding(self):
        record = {
            "instruction": "Convert the question to SQL.",
            "input": "Schema: orders(id)\nQuestion: List orders.",
        }

        prompt = build_direct_sql_prompt(record)

        self.assertIn("Schema: orders(id)", prompt)
        self.assertTrue(prompt.endswith("Return only the SQL query."))
        self.assertNotIn("PLAN_TYPE", prompt)
        self.assertNotIn("FINAL_SQL", prompt)

    def test_guided_prompt_adds_relationships_without_planning_labels(self):
        record = {
            "instruction": "Convert the question to SQL.",
            "input": "Schema: orders(customer_id)\nQuestion: List orders.",
            "metadata": {"db_id": "shop"},
        }

        prompt = build_direct_guided_prompt(
            record,
            {"shop": "Possible join keys:\norders.customer_id = customers.id"},
        )

        self.assertIn("orders.customer_id = customers.id", prompt)
        self.assertTrue(prompt.endswith("Return only the SQL query."))
        self.assertNotIn("PLAN_TYPE", prompt)
        self.assertNotIn("FINAL_SQL", prompt)

    def test_join_prompt_does_not_duplicate_column_ownership(self):
        record = {
            "instruction": "Convert the question to SQL.",
            "input": "Schema: orders(customer_id)\nQuestion: List orders.",
            "metadata": {"db_id": "shop"},
        }
        guidance = {
            "shop": "Column ownership:\norders: customer_id\n\n"
            "Possible join keys:\norders.customer_id = customers.id"
        }

        prompt = build_direct_join_prompt(record, guidance)

        self.assertIn("orders.customer_id = customers.id", prompt)
        self.assertNotIn("orders: customer_id", prompt)


if __name__ == "__main__":
    unittest.main()

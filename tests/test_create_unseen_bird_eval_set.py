import sys
import unittest
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_unseen_bird_eval_set import (
    choose_stratified_sample,
    eligible_records,
    normalize_question,
    proportional_allocations,
    schema_from_guidance,
)


class UnseenBirdEvalTests(unittest.TestCase):
    def test_excludes_prior_ids_and_normalized_questions(self):
        dev = [
            {"question_id": 1, "question": "New wording", "difficulty": "simple"},
            {"question_id": 2, "question": " Already   used ", "difficulty": "simple"},
            {"question_id": 3, "question": "Training question", "difficulty": "simple"},
            {"question_id": 4, "question": "Actually new", "difficulty": "simple"},
        ]
        mini = [{"input": "Schema: x\nQuestion: already used\nEvidence: x", "metadata": {"question_id": 1}}]
        train = [{"question": "training QUESTION"}]

        eligible = eligible_records(dev, mini, train)

        self.assertEqual([record["question_id"] for record in eligible], [4])

    def test_normalization_ignores_case_and_repeated_whitespace(self):
        self.assertEqual(normalize_question("  What   IS this? "), "what is this?")

    def test_proportional_allocation_uses_source_distribution(self):
        records = [
            *[{"difficulty": "simple"}] * 7,
            *[{"difficulty": "moderate"}] * 2,
            {"difficulty": "challenging"},
        ]
        self.assertEqual(
            proportional_allocations(records, 5),
            {"simple": 4, "moderate": 1, "challenging": 0},
        )

    def test_stratified_sample_is_deterministic(self):
        records = [
            {"question_id": index, "difficulty": "simple" if index < 8 else "moderate"}
            for index in range(10)
        ]
        first = choose_stratified_sample(records, 5, 42)
        second = choose_stratified_sample(records, 5, 42)
        self.assertEqual(first, second)
        self.assertEqual(Counter(row["difficulty"] for row in first), {"simple": 4, "moderate": 1})

    def test_extracts_schema_without_join_section(self):
        guidance = "Column ownership:\norders: id, customer_id\n\nPossible join keys:\norders.customer_id = customers.id"
        self.assertEqual(schema_from_guidance(guidance), "orders: id, customer_id")


if __name__ == "__main__":
    unittest.main()

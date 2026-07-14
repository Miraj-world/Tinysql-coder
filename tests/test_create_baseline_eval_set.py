import sys
import unittest
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_baseline_eval_set import choose_balanced_sample


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


if __name__ == "__main__":
    unittest.main()

import unittest

from scripts.prepare_sft_data_v10 import column_hint_score, relevant_column_hints


class ValueAlignedTrainingDataTests(unittest.TestCase):
    def test_question_relevant_column_scores_higher(self):
        query = "Which loans have status C?"
        status_score = column_hint_score("loan", "status", "Loan status such as C or D.", query)
        id_score = column_hint_score("loan", "account_id", "Account identifier.", query)
        self.assertGreater(status_score, id_score)

    def test_hints_are_limited_and_database_scoped(self):
        row = {"db_id": "bank", "question": "Which loans have status C?", "evidence": "status = C"}
        meanings = {
            "bank|loan|status": "Loan status such as C or D.",
            "bank|loan|amount": "Loan amount.",
            "other|loan|status": "Must not be included.",
        }
        hints = relevant_column_hints(row, meanings)
        self.assertTrue(hints[0].startswith("loan.status:"))
        self.assertFalse(any("Must not" in hint for hint in hints))


if __name__ == "__main__":
    unittest.main()

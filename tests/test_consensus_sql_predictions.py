import unittest

from scripts.consensus_sql_predictions import consensus_index


def result(rows=None, ok=True):
    return {"ok": ok, "rows": rows, "error": None}


class ConsensusSelectionTests(unittest.TestCase):
    def test_two_matching_non_empty_results_override_primary(self):
        selected, agreement = consensus_index(
            [result([[1]]), result([[2]]), result([[2]])]
        )
        self.assertEqual((selected, agreement), (1, 2))

    def test_empty_result_consensus_does_not_override_primary(self):
        selected, agreement = consensus_index(
            [result([[1]]), result([]), result([])]
        )
        self.assertEqual((selected, agreement), (0, 1))

    def test_tie_keeps_earliest_group(self):
        selected, agreement = consensus_index(
            [result([[1]]), result([[2]]), result([[2]]), result([[1]])]
        )
        self.assertEqual((selected, agreement), (0, 2))


if __name__ == "__main__":
    unittest.main()

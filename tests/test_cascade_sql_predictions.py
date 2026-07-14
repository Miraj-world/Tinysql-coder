import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cascade_sql_predictions import build_cascade, choose_prediction


def record(question_id: int, sql: str, db_id: str = "database") -> dict:
    return {
        "question_id": question_id,
        "db_id": db_id,
        "expected_sql": "SELECT correct",
        "predicted_sql": sql,
        "exact_match": False,
    }


def fake_executor(_db_id: str, sql: str) -> dict:
    if sql == "SELECT broken":
        return {"ok": False, "rows": None, "error": "syntax error"}
    return {"ok": True, "rows": [], "error": None}


class CascadePredictionTests(unittest.TestCase):
    def test_keeps_executable_primary_prediction(self):
        result = choose_prediction(
            record(1, "SELECT primary"),
            record(1, "SELECT fallback"),
            fake_executor,
        )

        self.assertEqual(result["predicted_sql"], "SELECT primary")
        self.assertFalse(result["cascade_used_fallback"])

    def test_uses_fallback_when_primary_cannot_execute(self):
        result = choose_prediction(
            record(1, "SELECT broken"),
            record(1, "SELECT fallback"),
            fake_executor,
        )

        self.assertEqual(result["predicted_sql"], "SELECT fallback")
        self.assertTrue(result["cascade_used_fallback"])
        self.assertEqual(result["cascade_primary_error"], "syntax error")

    def test_rejects_mismatched_prediction_sets(self):
        with self.assertRaisesRegex(ValueError, "different questions"):
            build_cascade(
                [record(1, "SELECT primary")],
                [record(2, "SELECT fallback")],
                fake_executor,
            )

    def test_rejects_mismatched_database(self):
        with self.assertRaisesRegex(ValueError, "database IDs"):
            choose_prediction(
                record(1, "SELECT primary", "one"),
                record(1, "SELECT fallback", "two"),
                fake_executor,
            )


if __name__ == "__main__":
    unittest.main()

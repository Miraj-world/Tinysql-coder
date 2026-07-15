import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.augment_eval_with_values import (
    add_value_hints,
    database_values,
    question_from_prompt,
    retrieval_text_from_prompt,
    value_score,
)


class ValueRetrievalTests(unittest.TestCase):
    def test_extracts_only_question_text(self):
        prompt = (
            "Schema:\npeople(name)\n"
            "Question: Which person lives in South Atlantic?\n"
            "Evidence: region name\n\nReturn only the SQL query."
        )
        self.assertEqual(question_from_prompt(prompt), "Which person lives in South Atlantic?")

    def test_exact_phrase_scores_above_unrelated_value(self):
        exact = value_score("South Atlantic", "clients in South Atlantic", "division")
        unrelated = value_score("Pacific", "clients in South Atlantic", "division")
        self.assertGreater(exact, unrelated)

    def test_retrieval_text_includes_visible_evidence(self):
        prompt = (
            "Question: Find female patients.\n"
            "Evidence: SEX = 'F'\n\nReturn only the SQL query."
        )
        self.assertEqual(retrieval_text_from_prompt(prompt), "Find female patients. SEX = 'F'")

    def test_short_value_needs_relevant_column(self):
        self.assertGreater(value_score("F", "female means sex F", "SEX"), 0)
        self.assertEqual(value_score("F", "female means sex F", "unrelated_id"), 0)

    def test_retrieves_relevant_sqlite_value_without_gold_sql(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            sqlite_path = Path(temporary_directory) / "test.sqlite"
            with closing(sqlite3.connect(sqlite_path)) as connection:
                connection.execute("CREATE TABLE district (division TEXT, code TEXT)")
                connection.executemany(
                    "INSERT INTO district VALUES (?, ?)",
                    [("South Atlantic", "SA"), ("Pacific", "PA")],
                )
                connection.commit()

            hints = database_values(sqlite_path, "clients in South Atlantic")

        self.assertIn("district.division: 'South Atlantic'", hints)
        self.assertFalse(any("Pacific" in hint for hint in hints))

    def test_adds_hints_before_return_instruction(self):
        prompt = "Question: Find it.\n\nReturn only the SQL query."
        augmented = add_value_hints(prompt, ["items.status: 'Active'"])
        self.assertLess(augmented.index("Relevant database values"), augmented.index("Return only"))


if __name__ == "__main__":
    unittest.main()

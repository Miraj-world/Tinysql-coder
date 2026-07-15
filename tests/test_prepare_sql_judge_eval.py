import unittest

from scripts.prepare_sql_judge_eval import candidate_section, judge_prompt


class SqlJudgePromptTests(unittest.TestCase):
    def test_excludes_failed_and_duplicate_candidates(self):
        candidates = [
            {"sql": "SELECT 1", "result": {"ok": True, "rows": [[1]]}},
            {"sql": " select  1 ", "result": {"ok": True, "rows": [[1]]}},
            {"sql": "SELECT bad", "result": {"ok": False, "rows": None}},
        ]
        section = candidate_section(candidates)
        self.assertEqual(section.count("Candidate "), 1)
        self.assertNotIn("SELECT bad", section)

    def test_places_candidates_before_return_instruction(self):
        prompt = "Question: Find it.\n\nReturn only the SQL query."
        judged = judge_prompt(prompt, "Candidate 1:\nSELECT 1")
        self.assertLess(judged.index("Candidate 1"), judged.index("Return only"))


if __name__ == "__main__":
    unittest.main()

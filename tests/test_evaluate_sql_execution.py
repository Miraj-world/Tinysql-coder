import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_sql_execution import execute_sql


class SqlExecutionTimeoutTests(unittest.TestCase):
    def setUp(self):
        temporary_file = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        temporary_file.close()
        self.sqlite_path = Path(temporary_file.name)
        connection = sqlite3.connect(self.sqlite_path)
        try:
            connection.execute("CREATE TABLE numbers (value INTEGER)")
            connection.execute("INSERT INTO numbers VALUES (1)")
            connection.commit()
        finally:
            connection.close()

    def tearDown(self):
        self.sqlite_path.unlink(missing_ok=True)

    def test_executes_small_query_within_limit(self):
        result = execute_sql(self.sqlite_path, "SELECT value FROM numbers", 1.0)

        self.assertEqual(result, {"ok": True, "rows": [[1]], "error": None})

    def test_interrupts_pathological_query(self):
        sql = """
        WITH RECURSIVE counter(value) AS (
            SELECT 1
            UNION ALL
            SELECT value + 1 FROM counter
        )
        SELECT SUM(value) FROM counter
        """

        result = execute_sql(self.sqlite_path, sql, 0.01)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "query timeout after 0.01 seconds")


if __name__ == "__main__":
    unittest.main()

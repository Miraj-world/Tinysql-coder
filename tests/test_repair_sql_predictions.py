import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.repair_sql_predictions import (
    undeclared_alias_repair_for_error,
    unqualified_column_repair_for_error,
)


SCHEMA = {
    "players": {"id", "height", "name"},
    "stats": {"id", "score"},
}


class UnqualifiedColumnRepairTests(unittest.TestCase):
    def test_qualifies_column_owned_by_exactly_one_joined_table(self):
        sql = (
            "SELECT p.name FROM players AS p "
            "INNER JOIN stats AS s ON p.id = s.id WHERE height > 180"
        )

        repair = unqualified_column_repair_for_error(sql, "no such column: height", SCHEMA)

        self.assertEqual(
            repair,
            (
                "SELECT p.name FROM players AS p "
                "INNER JOIN stats AS s ON p.id = s.id WHERE p.height > 180",
                "p",
                "height",
            ),
        )

    def test_does_not_repair_when_multiple_joined_tables_own_column(self):
        sql = "SELECT id FROM players AS p INNER JOIN stats AS s ON p.id = s.id"

        self.assertIsNone(
            unqualified_column_repair_for_error(sql, "ambiguous column name: id", SCHEMA)
        )

    def test_does_not_cross_nested_query_scopes(self):
        sql = (
            "SELECT p.name FROM (SELECT score FROM stats WHERE height > 180) AS s "
            "INNER JOIN players AS p ON p.id = s.id"
        )

        self.assertIsNone(
            unqualified_column_repair_for_error(sql, "no such column: height", SCHEMA)
        )

    def test_does_not_repair_single_table_query(self):
        sql = "SELECT name FROM players WHERE height > 180"

        self.assertIsNone(
            unqualified_column_repair_for_error(sql, "no such column: height", SCHEMA)
        )

    def test_preserves_literals_and_existing_qualified_references(self):
        sql = (
            "SELECT p.height FROM players AS p "
            "INNER JOIN stats AS s ON p.id = s.id "
            "WHERE height > 180 AND p.height < 220 AND p.name = 'height'"
        )

        repair = unqualified_column_repair_for_error(sql, "no such column: height", SCHEMA)

        self.assertEqual(
            repair[0],
            "SELECT p.height FROM players AS p "
            "INNER JOIN stats AS s ON p.id = s.id "
            "WHERE p.height > 180 AND p.height < 220 AND p.name = 'height'",
        )


class UndeclaredAliasRepairTests(unittest.TestCase):
    def test_replaces_undeclared_alias_with_single_owner(self):
        sql = "SELECT T1.name FROM players WHERE T1.height > 180"

        repair = undeclared_alias_repair_for_error(
            sql,
            "no such column: T1.name",
            SCHEMA,
        )

        self.assertEqual(
            repair,
            (
                "SELECT players.name FROM players WHERE T1.height > 180",
                "t1",
                "players",
                "name",
            ),
        )

    def test_rejects_column_owned_by_multiple_in_scope_tables(self):
        sql = "SELECT T1.id FROM players AS p INNER JOIN stats AS s ON p.id = s.id"

        self.assertIsNone(
            undeclared_alias_repair_for_error(sql, "no such column: T1.id", SCHEMA)
        )

    def test_rejects_owner_that_is_not_in_query(self):
        sql = "SELECT T1.height FROM stats AS s"

        self.assertIsNone(
            undeclared_alias_repair_for_error(sql, "no such column: T1.height", SCHEMA)
        )

    def test_rejects_nested_query(self):
        sql = "SELECT T1.name FROM (SELECT id FROM players) AS p"

        self.assertIsNone(
            undeclared_alias_repair_for_error(sql, "no such column: T1.name", SCHEMA)
        )

    def test_rejects_declared_alias(self):
        sql = "SELECT p.score FROM players AS p INNER JOIN stats AS s ON p.id = s.id"

        self.assertIsNone(
            undeclared_alias_repair_for_error(sql, "no such column: p.score", SCHEMA)
        )


if __name__ == "__main__":
    unittest.main()

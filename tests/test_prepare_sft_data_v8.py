import unittest

from scripts.prepare_sft_data_v8 import (
    build_user_message,
    choose_validation_databases,
    convert_row,
    schemas_from_column_meanings,
)


class PrepareSftDataV8Tests(unittest.TestCase):
    def test_schemas_from_column_meanings_groups_columns(self):
        meanings = {
            "db_one|orders|order_id": "identifier",
            "db_one|orders|amount": "money",
            "db_one|customers|customer_id": "identifier",
            "db_two|items|name": "item name",
        }

        schemas = schemas_from_column_meanings(meanings)

        self.assertEqual(schemas["db_one"], "customers(customer_id)\norders(order_id, amount)")
        self.assertEqual(schemas["db_two"], "items(name)")

    def test_validation_split_keeps_databases_whole(self):
        rows = [
            *[{"db_id": "a"} for _ in range(5)],
            *[{"db_id": "b"} for _ in range(4)],
            *[{"db_id": "c"} for _ in range(3)],
        ]

        first = choose_validation_databases(rows, validation_ratio=0.25, seed=42)
        second = choose_validation_databases(rows, validation_ratio=0.25, seed=42)

        self.assertEqual(first, second)
        self.assertTrue(first)
        self.assertLess(first, {"a", "b", "c"})

    def test_convert_row_teaches_plain_sql_and_keeps_evidence(self):
        row = {
            "db_id": "shop",
            "question": "How many orders are there?",
            "evidence": "orders means rows in orders",
            "SQL": "SELECT COUNT(*) FROM orders",
        }

        converted = convert_row(row, "orders(order_id)", "train")

        self.assertEqual(converted["messages"][-1]["content"], "SELECT COUNT(*) FROM orders")
        self.assertIn("Evidence: orders means rows in orders", converted["messages"][1]["content"])
        self.assertNotIn("FINAL_SQL", converted["messages"][-1]["content"])

    def test_build_user_message_omits_empty_evidence(self):
        row = {"db_id": "shop", "question": "List orders", "evidence": ""}

        prompt = build_user_message(row, "orders(order_id)")

        self.assertNotIn("Evidence:", prompt)
        self.assertTrue(prompt.endswith("Return only the SQL query."))

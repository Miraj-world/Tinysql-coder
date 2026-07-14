import unittest

from scripts.prepare_sft_data_v9 import (
    compact_schema,
    guidance_from_table_schema,
    join_guidance_from_table_schema,
)


SCHEMA = {
    "db_id": "shop",
    "table_names_original": ["customers", "orders"],
    "column_names_original": [
        [-1, "*"],
        [0, "id"],
        [0, "name"],
        [1, "id"],
        [1, "customer_id"],
    ],
    "foreign_keys": [[4, 1]],
}


class PrepareSftDataV9Tests(unittest.TestCase):
    def test_guidance_uses_declared_foreign_keys(self):
        guidance = guidance_from_table_schema(SCHEMA)

        self.assertIn("customers: id, name", guidance)
        self.assertIn("orders: id, customer_id", guidance)
        self.assertIn("orders.customer_id = customers.id", guidance)

    def test_compact_schema_uses_original_names(self):
        self.assertEqual(
            compact_schema(SCHEMA),
            "customers(id, name)\norders(id, customer_id)",
        )

    def test_join_guidance_does_not_repeat_column_ownership(self):
        guidance = join_guidance_from_table_schema(SCHEMA)

        self.assertEqual(guidance, "orders.customer_id = customers.id")
        self.assertNotIn("customers: id", guidance)

    def test_join_guidance_can_be_capped(self):
        schema = {
            **SCHEMA,
            "foreign_keys": [[4, 1], [3, 1]],
        }

        guidance = join_guidance_from_table_schema(schema, max_relationships=1)

        self.assertEqual(len(guidance.splitlines()), 1)

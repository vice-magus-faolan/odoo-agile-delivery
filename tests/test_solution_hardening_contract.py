"""Executable regression for lifecycle record serialization."""

import ast
import json
import unittest
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestSolutionHardeningContract(unittest.TestCase):
    def test_lifecycle_record_values_preserve_native_datetime_and_relations(self):
        # Load only the pure serializer: the complete probe owns a disposable DB.
        path = ROOT / "scripts/solution_lifecycle_probe.py"
        tree = ast.parse(path.read_text())
        helper = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "record_values"
        )
        namespace = {"json": json, "date": date, "datetime": datetime}
        exec(
            compile(ast.Module(body=[helper], type_ignores=[]), str(path), "exec"),
            namespace,
        )

        class Record:
            # Serializer fixture, not an inherited Odoo model read override.
            def read(self, fields):  # pylint: disable=method-required-super
                return [
                    {
                        "id": 7,
                        "task_id": (11, "SYNTHETIC Task"),
                        "event_at": datetime(2026, 10, 7, 2, 30, 1, 123456),
                        "date": date(2026, 10, 7),
                    }
                ]

        values = namespace["record_values"](Record(), ["task_id", "event_at", "date"])
        self.assertEqual(
            values,
            {
                "id": 7,
                "task_id": [11, "SYNTHETIC Task"],
                "event_at": "2026-10-07T02:30:01.123456",
                "date": "2026-10-07",
            },
        )

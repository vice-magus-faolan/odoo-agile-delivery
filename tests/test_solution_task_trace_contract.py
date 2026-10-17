"""Static boundary/discovery checks supplement, never replace native execution."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestTaskTraceContract(unittest.TestCase):
    def _text(self, path):
        return (ROOT / path).read_text()

    def test_optional_bridge_and_native_event_return_seam(self):
        core = ast.literal_eval(
            self._text("addons/project_agile_solution/__manifest__.py")
        )
        bridge = ast.literal_eval(
            self._text("addons/project_agile_solution_scrum/__manifest__.py")
        )
        self.assertEqual(core["depends"], ["project_agile"])
        self.assertEqual(bridge["depends"], ["project_agile_solution", "project_scrum"])
        self.assertEqual(bridge["license"], core["license"])
        self.assertIn(
            'return self.env["project.sprint.scope.event"].sudo().create(values)',
            self._text("addons/project_scrum/models/project_sprint.py"),
        )
        capture = self._text(
            "addons/project_agile_solution_scrum/models/sprint_context.py"
        )
        self.assertIn("super()._append_scope_events", capture)
        self.assertNotIn("def action_start", capture)
        self.assertNotIn("def action_close", capture)

    def test_core_and_bridge_have_real_imported_test_packages(self):
        for addon, test in (
            ("project_agile_solution", "test_solution_task_trace"),
            ("project_agile_solution_scrum", "test_sprint_context"),
        ):
            self.assertIn(
                "from . import " + test, self._text(f"addons/{addon}/tests/__init__.py")
            )
            self.assertTrue((ROOT / f"addons/{addon}/tests/{test}.py").is_file())
        self.assertIn(
            "CREATE",
            self._text(
                "addons/project_agile_solution/models/solution_task_intent.py"
            ).upper(),
        )

    def test_production_sources_never_commit_or_rollback_transactions(self):
        for path in (
            "addons/project_agile_solution/models/solution_task_intent.py",
            "addons/project_agile_solution/models/solution_task_link.py",
            "addons/project_agile_solution/models/solution_task_access.py",
            "addons/project_agile_solution_scrum/models/sprint_context.py",
        ):
            tree = ast.parse(self._text(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, {"commit", "rollback"}, path)

"""Structural regression checks for the Milestone 5 UI contract fixture."""

import ast
import unittest
from pathlib import Path


class TestProjectAgileUiContract(unittest.TestCase):
    """Keep the optional frontend boundary narrow and independently installable."""

    # Plain unittest.TestCase has no Odoo transaction setup to chain.
    def setUp(self):  # pylint: disable=method-required-super
        self.root = Path(__file__).resolve().parents[1]
        self.module_root = self.root / "addons" / "project_agile_ui"

    def test_manifest_uses_only_the_stable_scrum_backend(self):
        manifest = ast.literal_eval((self.module_root / "__manifest__.py").read_text())

        self.assertEqual(manifest["depends"], ["project_scrum"])
        self.assertTrue(manifest["installable"])
        self.assertEqual(
            manifest["assets"]["web.assets_unit_tests"],
            ["project_agile_ui/static/tests/**/*.test.js"],
        )
        self.assertNotIn("document_page_project_task", manifest["depends"])

    def test_frontend_fixture_uses_the_native_odoo_test_bundle(self):
        test_source = (
            self.module_root / "static" / "tests" / "planning_board_contract.test.js"
        ).read_text()

        self.assertIn('from "@odoo/hoot"', test_source)
        self.assertIn("test(", test_source)
        self.assertNotIn("QUnit", test_source)

    def test_contract_and_plan_record_scope_and_verification(self):
        adr = (
            self.root / "docs" / "adrs" / "010-advanced-agile-ui-contract.md"
        ).read_text()
        plan = (
            self.root / "docs" / "plans" / "2026-09-28-project-agile-ui-skeleton.md"
        ).read_text()
        readme = (self.root / "README.md").read_text()
        verify_script = (self.root / "scripts" / "verify").read_text()

        for boundary in (
            "No Git indicators",
            "No Task-document controls",
            "no duplicated backend business rules",
        ):
            self.assertIn(boundary, adr)
        self.assertIn("project_agile_ui", plan)
        self.assertIn("project_agile_ui", readme)
        self.assertIn("project_agile_ui", verify_script)


if __name__ == "__main__":
    unittest.main()

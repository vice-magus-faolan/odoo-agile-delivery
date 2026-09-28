"""Installation-level contract checks for the optional Agile UI shell."""

import ast
from pathlib import Path

from odoo.tests.common import TransactionCase


class TestProjectAgileUiModuleContract(TransactionCase):
    """Ensure the shell stays optional and uses Odoo's supported test bundle."""

    def test_module_is_installed_with_the_narrow_scrum_dependency(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = ast.literal_eval((module_root / "__manifest__.py").read_text())
        module = self.env["ir.module.module"].search([("name", "=", "project_agile_ui")])

        self.assertEqual(module.state, "installed")
        self.assertEqual(manifest["depends"], ["project_scrum"])
        self.assertEqual(
            manifest["assets"]["web.assets_unit_tests"],
            ["project_agile_ui/static/tests/**/*.test.js"],
        )

    def test_skeleton_has_no_data_or_backend_asset(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = ast.literal_eval((module_root / "__manifest__.py").read_text())

        self.assertNotIn("data", manifest)
        self.assertNotIn("web.assets_backend", manifest["assets"])

    def test_frontend_fixture_resolves_through_odoo_asset_discovery(self):
        """Use the exact Odoo 19 asset API only in this regression fixture."""
        asset_model = self.env["ir.asset"]
        asset_paths = asset_model._get_asset_paths(
            "web.assets_unit_tests", asset_model._get_asset_params()
        )

        self.assertTrue(
            any(
                path.endswith("/project_agile_ui/static/tests/planning_board_contract.test.js")
                for path, _full_path, _bundle, _modified in asset_paths
            )
        )

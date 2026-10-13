"""Installation-level contract checks for the optional Agile planning UI."""

import ast
from pathlib import Path

from odoo.tests.common import TransactionCase


class TestProjectAgileUiModuleContract(TransactionCase):
    """Keep the planning UI optional and discoverable through Odoo 19 assets."""

    def test_module_is_installed_with_the_narrow_scrum_dependency(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = ast.literal_eval((module_root / "__manifest__.py").read_text())
        module = self.env["ir.module.module"].search(
            [("name", "=", "project_agile_ui")]
        )

        self.assertEqual(module.state, "installed")
        self.assertEqual(manifest["depends"], ["project_scrum"])
        self.assertEqual(
            manifest["assets"]["web.assets_unit_tests"],
            ["project_agile_ui/static/tests/**/*.test.js"],
        )

    def test_module_declares_only_the_additive_planning_surfaces(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = ast.literal_eval((module_root / "__manifest__.py").read_text())

        self.assertEqual(manifest["data"], ["views/project_agile_ui_views.xml"])
        self.assertEqual(
            manifest["assets"]["web.assets_backend"],
            [
                "project_agile_ui/static/src/planning_board.js",
                "project_agile_ui/static/src/planning_board.xml",
                "project_agile_ui/static/src/planning_board.scss",
            ],
        )
        self.assertTrue(
            self.env.ref("project_agile_ui.view_project_form_agile_planning")
        )

    def test_frontend_fixture_resolves_through_odoo_asset_discovery(self):
        """Use the exact Odoo 19 asset API only in this regression fixture."""
        asset_model = self.env["ir.asset"]
        asset_paths = asset_model._get_asset_paths(
            "web.assets_unit_tests", asset_model._get_asset_params()
        )

        self.assertTrue(
            any(
                path.endswith(
                    "/project_agile_ui/static/tests/planning_board_contract.test.js"
                )
                for path, _full_path, _bundle, _modified in asset_paths
            )
        )

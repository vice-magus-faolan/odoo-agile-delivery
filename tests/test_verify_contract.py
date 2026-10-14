"""Regression checks for the safe Milestone 3 verification workflow."""

import unittest
from pathlib import Path


class TestVerifyContract(unittest.TestCase):
    def test_verification_covers_all_modules_and_lifecycles(self):
        root = Path(__file__).resolve().parents[1]
        verify_script = (root / "scripts" / "verify").read_text()

        self.assertIn(
            "MODULES=project_agile,project_scrum,project_scrum_analytics,project_agile_ui",
            verify_script,
        )
        self.assertIn(
            "TEST_TAGS=/project_agile,/project_scrum,/project_scrum_analytics,/project_agile_ui",
            verify_script,
        )
        self.assertIn('--update "$MODULES"', verify_script)
        self.assertIn("uninstall_module project_agile_ui", verify_script)
        self.assertIn("uninstall_module project_scrum_analytics", verify_script)
        self.assertIn("uninstall_module project_scrum", verify_script)
        self.assertIn("uninstall_module project_agile", verify_script)
        self.assertNotIn("dropdb -U odoo --if-exists --force", verify_script)
        self.assertIn("VERIFICATION_DATABASES", verify_script)
        self.assertIn("pg_terminate_backend", verify_script)
        self.assertIn("compose.verify.yaml", verify_script)
        self.assertIn(
            "FROM odoo:19.0",
            (root / "Dockerfile.verify").read_text(),
        )
        self.assertIn(
            "websocket-client==1.8.0",
            (root / "Dockerfile.verify").read_text(),
        )
        self.assertIn(
            "google-chrome-stable_154.0.8037.57-1_amd64.deb",
            (root / "Dockerfile.verify").read_text(),
        )
        self.assertIn(
            "66c0645f6a19871bab2844b8537c11a0db2e7d3bea8ef85a1c7cb52a54e65a3e",
            (root / "Dockerfile.verify").read_text(),
        )

    def test_planning_concurrency_harness_is_task_scoped_and_bounded(self):
        root = Path(__file__).resolve().parents[1]
        harness = (root / "scripts" / "test_planning_concurrency.py").read_text()
        worker = (root / "scripts" / "planning_concurrency_worker.py").read_text()

        self.assertIn("odoo_agile_planning_concurrency_t_b1f7013f", harness)
        self.assertIn("lock_timeout", worker)
        self.assertIn("statement_timeout", worker)
        self.assertIn("assign", harness)
        self.assertIn("reorder", harness)

    def test_server_modules_remain_free_of_custom_javascript_assets(self):
        root = Path(__file__).resolve().parents[1] / "addons"
        self.assertFalse((root / "project_scrum" / "static").exists())
        self.assertFalse((root / "project_scrum_analytics" / "static").exists())

    def test_ui_fixture_uses_the_odoo_native_test_asset(self):
        root = Path(__file__).resolve().parents[1] / "addons"
        self.assertTrue(
            (
                root
                / "project_agile_ui"
                / "static"
                / "tests"
                / "planning_board_contract.test.js"
            ).is_file()
        )

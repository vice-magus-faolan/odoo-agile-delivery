"""Regression checks for the safe Milestone 1 verification workflow."""

from pathlib import Path
import unittest


class TestVerifyContract(unittest.TestCase):
    def test_verification_covers_install_upgrade_and_reinstall_lifecycles(self):
        root = Path(__file__).resolve().parents[1]
        verify_script = (root / "scripts" / "verify").read_text()
        readme = (root / "README.md").read_text()

        self.assertIn("odoo_agile_verify_install", verify_script)
        self.assertIn("--update project_agile", verify_script)
        self.assertIn("button_immediate_uninstall", verify_script)
        self.assertNotIn("dropdb -U odoo --if-exists --force", verify_script)
        self.assertNotIn("36 Odoo tests", verify_script)
        self.assertIn("14 discovered project_agile", readme)
        self.assertIn("0 failed, 0 errors of 12 tests", readme)
        self.assertNotIn("38 passing tests", readme)

    def test_milestone_one_has_no_custom_javascript_assets(self):
        module_root = Path(__file__).resolve().parents[1] / "addons" / "project_agile"

        self.assertFalse((module_root / "static").exists())

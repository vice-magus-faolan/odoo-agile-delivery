"""Regression checks for the safe Milestone 2 verification workflow."""
from pathlib import Path
import unittest
class TestVerifyContract(unittest.TestCase):
    def test_verification_covers_both_modules_and_all_lifecycles(self):
        root = Path(__file__).resolve().parents[1]
        verify_script = (root / "scripts" / "verify").read_text()
        readme = (root / "README.md").read_text()
        self.assertIn("MODULES=project_agile,project_scrum", verify_script)
        self.assertIn("TEST_TAGS=/project_agile,/project_scrum", verify_script)
        self.assertIn('--update "$MODULES"', verify_script)
        self.assertIn("uninstall_module project_scrum", verify_script)
        self.assertIn("uninstall_module project_agile", verify_script)
        self.assertNotIn("dropdb -U odoo --if-exists --force", verify_script)
        self.assertIn("Milestone 2 verification boundary", readme)
        self.assertNotIn("Milestone 1 verification boundary", readme)
    def test_milestone_two_has_no_custom_javascript_assets(self):
        self.assertFalse(((Path(__file__).resolve().parents[1] / "addons" / "project_scrum") / "static").exists())

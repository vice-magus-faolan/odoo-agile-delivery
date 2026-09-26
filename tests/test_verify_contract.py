"""Regression checks for the safe Milestone 3 verification workflow."""

from pathlib import Path
import unittest


class TestVerifyContract(unittest.TestCase):
    def test_verification_covers_all_three_modules_and_lifecycles(self):
        root = Path(__file__).resolve().parents[1]
        verify_script = (root / "scripts" / "verify").read_text()
        readme = (root / "README.md").read_text()

        self.assertIn(
            "MODULES=project_agile,project_scrum,project_scrum_analytics", verify_script
        )
        self.assertIn(
            "TEST_TAGS=/project_agile,/project_scrum,/project_scrum_analytics",
            verify_script,
        )
        self.assertIn('--update "$MODULES"', verify_script)
        self.assertIn("uninstall_module project_scrum_analytics", verify_script)
        self.assertIn("uninstall_module project_scrum", verify_script)
        self.assertIn("uninstall_module project_agile", verify_script)
        self.assertNotIn("dropdb -U odoo --if-exists --force", verify_script)
        self.assertIn("Milestone 3 verification boundary", readme)
        self.assertNotIn("Milestone 2 verification boundary", readme)

    def test_milestone_three_has_no_custom_javascript_assets(self):
        root = Path(__file__).resolve().parents[1] / "addons"
        self.assertFalse((root / "project_scrum" / "static").exists())
        self.assertFalse((root / "project_scrum_analytics" / "static").exists())

    def test_recovery_documentation_matches_the_lifecycle_guard(self):
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text()
        analytics_readme = (
            root / "addons" / "project_scrum_analytics" / "README.md"
        ).read_text()
        analytics_adr = (root / "docs" / "adrs" / "009-scrum-analytics-semantics.md").read_text()
        scope_adr = (root / "docs" / "adrs" / "003-sprint-scope-history-strategy.md").read_text()

        for document in (readme, analytics_readme, analytics_adr, scope_adr):
            document = " ".join(document.split())
            self.assertIn("Superuser recovery may correct `closed_at`", document)
            self.assertIn("lifecycle state remains action-only", document)

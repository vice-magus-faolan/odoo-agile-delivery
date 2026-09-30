"""Static guards for the optional Milestone 7 contract fixture."""

import ast
from pathlib import Path
import unittest


class TestGitAutomationContract(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.addon = self.root / "addons" / "project_agile_git_automation"

    def test_independent_optional_skeleton(self):
        manifest = ast.literal_eval((self.addon / "__manifest__.py").read_text())
        self.assertEqual(manifest["depends"], ["project_agile_git"])
        self.assertEqual(manifest["license"], "LGPL-3")
        self.assertTrue(manifest["installable"])
        self.assertFalse(manifest.get("auto_install", False))
        for path in (self.root / "addons").glob("*/__manifest__.py"):
            if path.parent == self.addon:
                continue
            self.assertNotIn("project_agile_git_automation", ast.literal_eval(path.read_text())["depends"])

    def test_no_evaluator_task_override_or_scheduler(self):
        sources = list((self.addon / "models").glob("*.py"))
        combined = "\n".join(path.read_text() for path in sources)
        self.assertNotIn('_inherit = "project.task"', combined)
        self.assertNotIn("stage_id", combined)
        self.assertNotIn("_cron", combined)
        self.assertFalse((self.addon / "controllers").exists())
        self.assertFalse((self.addon / "data").exists())
        self.assertIn("from . import test_policy_contract", (self.addon / "tests" / "__init__.py").read_text())

    def test_contract_excludes_template_driven_nontransactional_effects(self):
        contract = (self.root / "docs" / "adrs" / "012-git-workflow-policy-contract.md").read_text()
        for boundary in ("rating_active", "mail_template_id", "sms_template_id", "put_in_queue=False"):
            self.assertTrue(boundary in contract, f"Missing explicit notification boundary: {boundary}")
        self.assertIn("rejects target stages", contract)
        self.assertIn("not transactionally", contract)

    def test_verifier_preserves_existing_modules_and_adds_optional_lifecycle(self):
        script = (self.root / "scripts" / "verify").read_text()
        self.assertIn(
            "MODULES=project_agile,project_scrum,project_scrum_analytics,project_agile_ui,project_agile_git,project_agile_git_github,project_agile_git_automation",
            script,
        )
        self.assertIn("/project_agile_git_automation", script)
        self.assertLess(script.index("uninstall_module project_agile_git_automation"), script.index("uninstall_module project_agile_git\n"))
        self.assertIn('run_odoo --database "$DATABASE_INSTALL" --init project_agile_git_automation', script)
        self.assertIn("Milestone 5 planning-board verification passed.", script)
        self.assertIn("Milestone 6 Git facts contract verification passed.", script)


if __name__ == "__main__":
    unittest.main()

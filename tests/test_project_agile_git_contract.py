"""Regression checks for the Milestone 6 Git facts boundary."""

import ast
from pathlib import Path
import unittest


class TestProjectAgileGitContract(unittest.TestCase):
    """Keep Git facts provider-neutral, native-scheduled, and independent."""

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.module_root = self.root / "addons" / "project_agile_git"

    def test_manifest_is_small_and_does_not_adopt_a_provider_or_queue_runtime(self):
        manifest = ast.literal_eval((self.module_root / "__manifest__.py").read_text())

        self.assertEqual(manifest["depends"], ["project_agile"])
        self.assertTrue(manifest["installable"])
        self.assertNotIn("queue_job", manifest["depends"])
        self.assertNotIn("project_github", manifest["depends"])
        self.assertNotIn("project_gitlab", manifest["depends"])

    def test_skeleton_declares_the_provider_neutral_contract_models(self):
        source = (self.module_root / "models" / "project_git_fact.py").read_text()

        for model in (
            "project.git.repository",
            "project.git.delivery",
            "project.git.branch",
            "project.git.commit",
            "project.git.pull.request",
            "project.git.check",
            "project.git.task.association",
        ):
            self.assertIn(f'_name = "{model}"', source)
        self.assertIn("UNIQUE(repository_id, provider_delivery_id)", source)
        self.assertIn("lease_token", source)
        self.assertIn("lease_expires_at", source)
        self.assertIn("An Agile key association is immutable.", source)
        self.assertIn("_check_company_auto = True", source)

    def test_contract_keeps_webhook_and_workflow_policy_out_of_the_skeleton(self):
        module_files = "\n".join(
            path.relative_to(self.module_root).as_posix()
            for path in self.module_root.rglob("*")
            if path.is_file()
        )

        self.assertNotIn("controllers/", module_files)
        self.assertNotIn("static/", module_files)
        self.assertNotIn("automation", module_files.lower())

    def test_accepted_adr_selects_native_portable_scheduling_not_queue_job(self):
        adr = (self.root / "docs" / "adrs" / "011-git-facts-and-visibility-contract.md").read_text()
        verify_script = (self.root / "scripts" / "verify").read_text()
        module_readme = (self.module_root / "README.md").read_text()

        self.assertIn("Odoo.sh", adr)
        self.assertIn("ir.cron", adr)
        self.assertIn("_commit_progress", adr)
        self.assertIn("expiring processing lease", adr)
        self.assertIn("Reject OCA `queue_job`", adr)
        self.assertIn("workflow automation", adr.lower())
        self.assertNotIn("verify-oca-queue-job", verify_script)
        self.assertIn("project_agile_git", verify_script)
        self.assertIn("Odoo 19 `ir.cron`", module_readme)
        self.assertNotIn("accepted OCA `queue_job`", module_readme)

    def test_security_keeps_facts_within_project_visibility_and_company_scope(self):
        security = (self.module_root / "security" / "project_agile_git_security.xml").read_text()

        self.assertEqual(security.count("multi-company"), 7)
        self.assertEqual(security.count("Project visibility"), 7)
        self.assertEqual(security.count("Project manager"), 7)
        self.assertIn("project_id.message_partner_ids", security)
        self.assertIn("repository_id.project_id.message_partner_ids", security)

    def test_verifier_uses_an_isolated_worktree_compose_namespace(self):
        verify_script = (self.root / "scripts" / "verify").read_text()

        self.assertIn("DEFAULT_COMPOSE_PROJECT_NAME=", verify_script)
        self.assertIn(
            'COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$DEFAULT_COMPOSE_PROJECT_NAME}"',
            verify_script,
        )
        self.assertIn("export COMPOSE_PROJECT_NAME", verify_script)
        self.assertIn("COMPOSE_PROJECT_NAME_WAS_SET=false", verify_script)
        self.assertIn("if [[ $COMPOSE_PROJECT_NAME_WAS_SET == false ]]", verify_script)
        self.assertIn("trap cleanup_verification_resources EXIT", verify_script)
        self.assertIn('"${COMPOSE[@]}" down --volumes --remove-orphans', verify_script)


if __name__ == "__main__":
    unittest.main()

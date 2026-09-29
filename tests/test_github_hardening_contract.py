"""Static release-gate contracts for GitHub hardening and recovery."""

from pathlib import Path
import unittest


class TestGitHubHardeningContract(unittest.TestCase):
    """Keep the full GitHub lifecycle and runbook in the canonical verifier."""

    def test_verifier_cannot_omit_the_adapter_or_dependency_safe_uninstall(self):
        root = Path(__file__).resolve().parents[1]
        verify_script = (root / "scripts" / "verify").read_text()

        self.assertIn(
            "MODULES=project_agile,project_scrum,project_scrum_analytics,project_agile_ui,project_agile_git,project_agile_git_github",
            verify_script,
        )
        self.assertIn(
            "TEST_TAGS=/project_agile,/project_scrum,/project_scrum_analytics,/project_agile_ui,/project_agile_git,/project_agile_git_github",
            verify_script,
        )
        self.assertIn('run_odoo --database "$DATABASE_UPGRADE" --update "$MODULES"', verify_script)
        self.assertLess(
            verify_script.index("uninstall_module project_agile_git_github"),
            verify_script.index("\nuninstall_module project_agile_git\n"),
        )
        self.assertIn("python3 -m compileall -q addons", verify_script)

    def test_operator_runbook_keeps_recovery_authenticated_and_database_free(self):
        root = Path(__file__).resolve().parents[1]
        runbook = (root / "docs" / "runbooks" / "github-git-facts-operations.md").read_text()

        for heading in (
            "Rotate a repository webhook secret",
            "Disable a repository safely",
            "Diagnose delivery and retry",
            "Retention and cleanup",
            "Rollback",
        ):
            self.assertIn(heading, runbook)
        self.assertIn("do not edit PostgreSQL rows", runbook)
        self.assertIn("do not run ad-hoc SQL", runbook)
        self.assertIn(
            "never purges `queued`, `processing`, `retryable`, or `failed`",
            " ".join(runbook.split()),
        )


if __name__ == "__main__":
    unittest.main()

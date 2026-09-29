"""Static contracts for the isolated GitHub delivery ingress adapter."""

import ast
from pathlib import Path
import unittest


class TestProjectAgileGitHubContract(unittest.TestCase):
    """Keep provider ingress narrow, authenticated, and outside the core addon."""

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.adapter_root = self.root / "addons" / "project_agile_git_github"

    def test_adapter_is_separate_from_the_provider_neutral_core(self):
        manifest = ast.literal_eval((self.adapter_root / "__manifest__.py").read_text())

        self.assertEqual(manifest["depends"], ["project_agile_git"])
        self.assertTrue(manifest["installable"])
        self.assertNotIn("queue_job", manifest["depends"])

    def test_controller_has_the_authenticated_persistence_only_boundary(self):
        source = (self.adapter_root / "controllers" / "github_webhook.py").read_text()

        self.assertIn('auth="public"', source)
        self.assertIn('methods=["POST"]', source)
        self.assertIn("csrf=False", source)
        self.assertIn("MAX_BODY_BYTES", source)
        self.assertIn("hmac.compare_digest", source)
        self.assertIn("X-Hub-Signature-256", source)
        self.assertIn("_record_authenticated_github_delivery", source)
        self.assertNotIn("project.task", source)
        self.assertNotIn("sudo()", source)

    def test_canonical_verifier_installs_the_provider_adapter(self):
        verify_script = (self.root / "scripts" / "verify").read_text()

        self.assertIn("project_agile_git_github", verify_script)


if __name__ == "__main__":
    unittest.main()

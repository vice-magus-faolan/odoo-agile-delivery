"""Discovery guards for the runtime signed-lifecycle and duplicate-race regressions."""

import ast
import unittest
from pathlib import Path


class TestGitPolicyProvenanceContract(unittest.TestCase):
    # Plain unittest.TestCase has no Odoo transaction setup to chain.
    def setUp(self):  # pylint: disable=method-required-super
        self.root = Path(__file__).resolve().parents[1]

    def test_current_duplicate_decisions_retain_resolved_task(self):
        path = (
            self.root
            / "addons/project_agile_git_github/models/project_github_normalizer.py"
        )
        tree = ast.parse(path.read_text())
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_associate_agile_key"
        )
        duplicates = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_record_association_audit"
            and len(node.args) > 4
            and isinstance(node.args[4], ast.Constant)
            and node.args[4].value == "already_associated"
        ]
        self.assertEqual(len(duplicates), 2)
        for call in duplicates:
            self.assertEqual(ast.unparse(call.args[-1]), "task")
        domain = next(
            node.value
            for node in ast.walk(method)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "association_domain"
                for target in node.targets
            )
        )
        assert isinstance(domain, ast.List)
        self.assertEqual(
            {row.elts[0].value for row in domain.elts},
            {
                "repository_id",
                "company_id",
                "task_id",
                "agile_key",
                "source_type",
                "source_provider_id",
            },
        )
        handler = next(
            node for node in ast.walk(method) if isinstance(node, ast.ExceptHandler)
        )
        self.assertIn(
            "association_model.search(association_domain, limit=1)",
            ast.unparse(handler),
        )
        self.assertTrue(any(isinstance(node, ast.Raise) for node in ast.walk(handler)))

    def test_optional_lifecycle_tests_are_imported_without_runtime_dependency(self):
        addon = self.root / "addons/project_agile_git_automation"
        manifest = ast.literal_eval((addon / "__manifest__.py").read_text())
        self.assertEqual(manifest["depends"], ["project_agile_git"])
        self.assertIn(
            "from . import test_policy_github_lifecycle",
            (addon / "tests/__init__.py").read_text(),
        )
        source = (addon / "tests/test_policy_github_lifecycle.py").read_text()
        self.assertIn("self.skipTest", source)
        self.assertIn("GitHubWebhookController", source)
        self.assertIn(
            "test_signed_opened_merge_and_repeated_update_keep_current_task_proof",
            source,
        )
        self.assertIn(
            "test_foreign_and_unknown_keys_have_identical_taskless_diagnostics", source
        )
        self.assertIn(
            "test_archived_duplicate_does_not_gain_current_task_proof", source
        )

    def test_canonical_gate_includes_independent_duplicate_race(self):
        self.assertIn(
            '"$ROOT/scripts/github_association_concurrency_probe.py"',
            (self.root / "scripts/verify").read_text(),
        )
        for name in ("probe", "worker"):
            source = (
                self.root / f"scripts/github_association_concurrency_{name}.py"
            ).read_text()
            self.assertIn('env.cr.dbname == "odoo_agile_verify_install"', source)
        worker = (
            self.root / "scripts/github_association_concurrency_worker.py"
        ).read_text()
        self.assertIn("env.cr.rollback()", worker)
        self.assertIn("rolled_back_delivery_has_no_audit", worker)


if __name__ == "__main__":
    unittest.main()

"""Static guards for the optional Milestone 7 dry-run boundary."""

import ast
import hashlib
import importlib.util
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

    def test_no_policy_task_write_or_scheduler(self):
        sources = list((self.addon / "models").glob("*.py"))
        combined = "\n".join(path.read_text() for path in sources)
        # Jimmy's approved R2 amendment permits exactly this revoke-only observer,
        # not a policy Task effect, configurable dispatch, or concurrency field.
        hook = self.addon / "models" / "project_task.py"
        self.assertEqual([p.name for p in sources if '_inherit = "project.task"' in p.read_text()], [hook.name])
        tree = ast.parse(hook.read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        self.assertEqual({n.name for n in cls.body if isinstance(n, ast.FunctionDef)},
                         {"create", "write", "unlink", "_git_policy_affected_projects", "_git_policy_lock_scopes", "_git_policy_requested_scopes"})
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"create", "write", "unlink"}:
                self.assertIsInstance(node.func.value, ast.Call)
                self.assertEqual(node.func.value.func.id, "super")
        self.assertNotIn("fields.", hook.read_text())
        self.assertIn("_revoke(", hook.read_text())
        self.assertNotIn('write({"stage_id"', combined)
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

    def test_dry_run_model_discovery_and_no_effect_consumption(self):
        models = (self.addon / "models" / "__init__.py").read_text()
        tests = (self.addon / "tests" / "__init__.py").read_text()
        for model in ("project_git_policy_observation", "project_git_policy_evaluation"):
            self.assertIn("from . import " + model, models)
        self.assertIn("from . import test_policy_evaluation", tests)
        source = (self.addon / "models" / "project_git_policy_evaluation.py").read_text()
        self.assertIn("action_dry_run_git_policy", source)
        self.assertNotIn("project.git.policy.effect", source)
        self.assertNotIn("project.git.policy.attempt", source)
        self.assertNotIn("retained_payload", source)
        self.assertFalse((self.addon / "models" / "project_git_policy_execution.py").exists())

    def test_versioned_evidence_golden_serialization_and_failure_precedence(self):
        path = self.addon / "models" / "policy_evidence.py"
        spec = importlib.util.spec_from_file_location("policy_evidence", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        evidence = {"version": 1, "task": {"stage": 2, "key": "ENG-1"}, "checks": []}
        golden = b'{"checks":[],"task":{"key":"ENG-1","stage":2},"version":1}'
        self.assertEqual(module.canonical(evidence).encode(), golden)
        self.assertEqual(module.fingerprint(evidence), hashlib.sha256(golden).hexdigest())
        self.assertEqual(module.reduce_conditions([("waiting", "missing_check"), ("rejected", "check_failed")]),
                         ("rejected", "check_failed"))
        for size in (40, 64):
            self.assertIsNotNone(module.FULL_SHA.fullmatch("A" * size))
        for value in ("a" * 39, "a" * 41, " a" * 20, "a" * 40 + "\n", "g" * 40):
            self.assertIsNone(module.FULL_SHA.fullmatch(value))

    def test_task_specific_search_uses_live_native_query_not_sudo_ids(self):
        source = (self.addon / "models" / "project_git_policy_observation.py").read_text()
        self.assertIn('self.env["project.task"]._search([], active_test=False)', source)
        self.assertIn('Domain("task_id", "in", tasks)', source)
        self.assertNotIn('sudo().search(', source)
        self.assertIn("Only the validated private observation producer", source)


if __name__ == "__main__":
    unittest.main()

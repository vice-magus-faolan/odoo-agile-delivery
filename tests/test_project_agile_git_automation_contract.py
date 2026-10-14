"""Static guards for the optional Milestone 7 dry-run boundary."""

import ast
import hashlib
import importlib.util
import unittest
from pathlib import Path


class TestGitAutomationContract(unittest.TestCase):
    # Plain unittest.TestCase has no Odoo transaction setup to chain.
    def setUp(self):  # pylint: disable=method-required-super
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
            self.assertNotIn(
                "project_agile_git_automation",
                ast.literal_eval(path.read_text())["depends"],
            )

    def test_typed_stage_only_writer_and_separate_scheduler(self):
        sources = list((self.addon / "models").glob("*.py"))
        combined = "\n".join(path.read_text() for path in sources)
        # Apply adds the server-owned fence to the same narrow native observer.
        hook = self.addon / "models" / "project_task.py"
        self.assertEqual(
            [p.name for p in sources if '_inherit = "project.task"' in p.read_text()],
            [hook.name],
        )
        tree = ast.parse(hook.read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        self.assertEqual(
            {n.name for n in cls.body if isinstance(n, ast.FunctionDef)},
            {
                "create",
                "write",
                "unlink",
                "_git_policy_affected_projects",
                "_git_policy_lock_scopes",
                "_git_policy_requested_scopes",
                "_git_policy_fence_tasks",
                "_compute_state",
                "_git_policy_advance_transition",
            },
        )
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"create", "write", "unlink"}
            ):
                self.assertIsInstance(node.func.value, ast.Call)
                self.assertEqual(node.func.value.func.id, "super")
        self.assertIn(
            "git_policy_transition_version = fields.Integer", hook.read_text()
        )
        self.assertIn("_revoke(", hook.read_text())
        writer = self.addon / "models" / "project_git_policy_execution.py"
        effect_calls = [
            n
            for n in ast.walk(ast.parse(writer.read_text()))
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "task"
            and n.func.attr == "write"
        ]
        self.assertEqual(len(effect_calls), 1)
        self.assertEqual(
            [key.value for key in effect_calls[0].args[0].keys], ["stage_id"]
        )
        self.assertIn("with_user(activation.execution_user_id)", writer.read_text())
        self.assertNotIn("task.sudo().write", combined)
        self.assertNotIn("cr.commit(", combined)
        self.assertNotIn("cr.rollback(", combined)
        self.assertFalse((self.addon / "controllers").exists())
        self.assertTrue((self.addon / "data" / "project_git_policy_cron.xml").exists())
        self.assertIn(
            "from . import test_policy_contract",
            (self.addon / "tests" / "__init__.py").read_text(),
        )

    def test_native_state_observer_preserves_compute(self):
        hook = self.addon / "models" / "project_task.py"
        tree = ast.parse(hook.read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        compute = next(
            node
            for node in cls.body
            if isinstance(node, ast.FunctionDef) and node.name == "_compute_state"
        )
        mutations = [
            node
            for node in ast.walk(compute)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Attribute) for target in node.targets)
        ]
        self.assertFalse(mutations, "Observer must not assign native business fields")
        self.assertIn("super()._compute_state()", ast.unparse(compute))
        self.assertIn("depend_on_ids.state", ast.unparse(compute))

    def test_contract_excludes_template_driven_nontransactional_effects(self):
        contract = (
            self.root / "docs" / "adrs" / "012-git-workflow-policy-contract.md"
        ).read_text()
        for boundary in (
            "rating_active",
            "mail_template_id",
            "sms_template_id",
            "put_in_queue=False",
        ):
            self.assertTrue(
                boundary in contract,
                f"Missing explicit notification boundary: {boundary}",
            )
        self.assertIn("rejects target stages", " ".join(contract.split()))
        self.assertIn("not transactionally", " ".join(contract.split()))

    def test_verifier_preserves_existing_modules_and_adds_optional_lifecycle(self):
        script = (self.root / "scripts" / "verify").read_text()
        self.assertIn(
            "MODULES=project_agile,project_scrum,project_scrum_analytics,project_agile_ui,project_agile_git,project_agile_git_github,project_agile_git_automation",
            script,
        )
        self.assertIn("/project_agile_git_automation", script)
        self.assertLess(
            script.index("uninstall_module project_agile_git_automation"),
            script.index("uninstall_module project_agile_git\n"),
        )
        self.assertIn(
            'run_odoo --database "$DATABASE_INSTALL" '
            "--init project_agile_git_automation",
            script,
        )
        self.assertIn("Milestone 5 planning-board verification passed.", script)
        self.assertIn("Milestone 6 Git facts contract verification passed.", script)

    def test_dry_run_model_discovery_and_no_effect_consumption(self):
        models = (self.addon / "models" / "__init__.py").read_text()
        tests = (self.addon / "tests" / "__init__.py").read_text()
        for model in (
            "project_git_policy_observation",
            "project_git_policy_evaluation",
        ):
            self.assertIn("from . import " + model, models)
        self.assertIn("from . import test_policy_evaluation", tests)
        source = (
            self.addon / "models" / "project_git_policy_evaluation.py"
        ).read_text()
        self.assertIn("action_dry_run_git_policy", source)
        self.assertNotIn("project.git.policy.effect", source)
        self.assertNotIn("project.git.policy.attempt", source)
        self.assertNotIn("retained_payload", source)
        self.assertTrue(
            (self.addon / "models" / "project_git_policy_execution.py").exists()
        )

    def test_versioned_evidence_golden_serialization_and_failure_precedence(self):
        path = self.addon / "models" / "policy_evidence.py"
        spec = importlib.util.spec_from_file_location("policy_evidence", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        evidence = {"version": 1, "task": {"stage": 2, "key": "ENG-1"}, "checks": []}
        golden = b'{"checks":[],"task":{"key":"ENG-1","stage":2},"version":1}'
        self.assertEqual(module.canonical(evidence).encode(), golden)
        self.assertEqual(
            module.fingerprint(evidence), hashlib.sha256(golden).hexdigest()
        )
        self.assertEqual(
            module.reduce_conditions(
                [("waiting", "missing_check"), ("rejected", "check_failed")]
            ),
            ("rejected", "check_failed"),
        )
        for size in (40, 64):
            self.assertIsNotNone(module.FULL_SHA.fullmatch("A" * size))
        for value in ("a" * 39, "a" * 41, " a" * 20, "a" * 40 + "\n", "g" * 40):
            self.assertIsNone(module.FULL_SHA.fullmatch(value))

    def test_task_specific_search_uses_live_native_query_not_sudo_ids(self):
        source = (
            self.addon / "models" / "project_git_policy_observation.py"
        ).read_text()
        self.assertIn('self.env["project.task"]._search([], active_test=False)', source)
        self.assertIn('Domain("task_id", "in", tasks)', source)
        self.assertNotIn("sudo().search(", source)
        self.assertIn("Only the validated private observation producer", source)


if __name__ == "__main__":
    unittest.main()

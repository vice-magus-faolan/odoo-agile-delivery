"""Static wiring guards; real ORM/tour/progress checks supply runtime evidence."""
import ast
from pathlib import Path
import unittest
from xml.etree import ElementTree


class TestGitPolicyOperationsContract(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.addon = self.root / "addons/project_agile_git_automation"

    def test_native_operations_views_are_discovered_and_read_only(self):
        manifest = ast.literal_eval((self.addon / "__manifest__.py").read_text())
        self.assertIn("views/project_git_policy_operations_views.xml", manifest["data"])
        xml = ElementTree.parse(self.addon / "views/project_git_policy_operations_views.xml")
        records = {row.attrib["id"]: row for row in xml.findall("record")}
        for name in ("attempt", "effect", "activation"):
            record = records[f"view_git_policy_{name}_form"]
            form = record.find("field[@name='arch']/form")
            self.assertIsNotNone(form)
            assert form is not None
            self.assertEqual({key: form.attrib[key] for key in ("create", "edit", "delete")},
                             {"create": "0", "edit": "0", "delete": "0"})
        fields = {row.attrib["name"] for row in xml.findall(".//field")}
        for name in ("activated_at", "approver_id", "execution_user_id", "before_stage_id", "after_stage_id",
                     "observation_id", "attempt_count", "event_ids", "actor_id"):
            self.assertIn(name, fields)
        combined = "".join(path.read_text() for path in (self.addon / "views").glob("*.xml"))
        self.assertNotIn("t-raw", combined)
        self.assertNotIn('widget="html"', combined)
        self.assertNotIn('name="lease_token"', combined)

    def test_retry_signature_and_mutations_cannot_widen_candidate(self):
        source = (self.addon / "models/project_git_policy_execution.py").read_text()
        tree = ast.parse(source)
        retry = next(row for row in ast.walk(tree) if isinstance(row, ast.FunctionDef) and row.name == "action_retry")
        self.assertEqual([arg.arg for arg in retry.args.args], ["self"])
        self.assertIsNone(retry.args.kwarg)
        schedule = next(row for row in ast.walk(retry) if isinstance(row, ast.Call)
                        and isinstance(row.func, ast.Attribute) and row.func.attr == "_set_schedule")
        values = schedule.args[0]
        self.assertIsInstance(values, ast.Dict)
        assert isinstance(values, ast.Dict)
        self.assertEqual({ast.literal_eval(key) for key in values.keys},
                         {"state", "reason", "next_retry_at", "lease_token", "lease_expires_at"})
        reads = [row for row in ast.walk(retry) if isinstance(row, ast.Call)
                 and isinstance(row.func, ast.Attribute) and row.func.attr == "check_access"]
        self.assertEqual([ast.literal_eval(row.args[0]) for row in reads], ["read", "read"])
        self.assertIn("require_capability", ast.unparse(retry))
        self.assertIn("_check_retry_candidate", ast.unparse(retry))

    def test_no_production_js_or_new_runtime_service_dependency(self):
        manifest = ast.literal_eval((self.addon / "__manifest__.py").read_text())
        self.assertEqual(set(manifest["assets"]), {"web.assets_tests"})
        self.assertEqual(manifest["depends"], ["project_agile_git"])
        self.assertNotIn("external_dependencies", manifest)
        imports = set()
        for file in (self.addon / "models").glob("*.py"):
            for row in ast.walk(ast.parse(file.read_text())):
                if isinstance(row, ast.Import):
                    imports.update(item.name for item in row.names)
                if isinstance(row, ast.ImportFrom) and row.module:
                    imports.add(row.module)
        for forbidden in ("requests", "subprocess", "socket", "queue_job", "github"):
            self.assertFalse(any(name.split(".")[0] == forbidden for name in imports))

    def test_canonical_gate_discovers_tours_and_constrained_runtime(self):
        tests = (self.addon / "tests/__init__.py").read_text()
        self.assertIn("from . import test_policy_operations", tests)
        self.assertIn("from . import test_policy_operations_tour", tests)
        verify = (self.root / "scripts/verify").read_text()
        self.assertIn("python3 -m compileall -q addons scripts", verify)
        self.assertIn("controls, dry-run, apply and recovery verification passed", verify)
        overlay = (self.root / "compose.verify.yaml").read_text()
        for boundary in ("read_only: true", "./addons:/mnt/extra-addons:ro", "internal: true"):
            self.assertIn(boundary, overlay)
        probe = (self.root / "scripts/git_policy_concurrency_probe.py").read_text()
        self.assertIn("native_budget_after_discovery", probe)
        self.assertIn("native_budget_after_settlement_recovery", probe)
        self.assertIn("commit_progress(self, *args, **kwargs)", probe)

    def test_runbook_and_current_scope_are_not_activation_claims(self):
        text = (self.root / "docs/runbooks/git-policy-operations.md").read_text()
        for boundary in ("dry-run-before-enable", "Disable does NOT undo", "five-claim budget",
                         "staging", "five minutes", "tombstones", "database and filestore", "NOT a live Odoo.sh"):
            self.assertIn(boundary, text)
        readme = (self.root / "README.md").read_text()
        self.assertNotIn("task-stage execution remain pending", readme)
        self.assertNotIn("There is no cron", readme)
        self.assertIn("No production policy", readme)


if __name__ == "__main__":
    unittest.main()

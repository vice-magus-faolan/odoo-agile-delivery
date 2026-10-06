"""Static discovery/fixture checks complement real Odoo installation, never replace it."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addons" / "project_agile_solution"


class TestSolutionContract(unittest.TestCase):
    def test_review_artifacts_preserve_scope_and_seeded_graph(self):
        scope = ROOT / "docs" / "milestone-8-approved-scope.md"
        self.assertEqual(
            hashlib.sha256(scope.read_bytes()).hexdigest(),
            "5a3e4a5c374d3d9d668031ae358825976e6beb0831eaa51f5283273ba0c08326",
        )
        paths = (
            "docs/adrs/013-solution-definition-contract.md",
            "docs/plans/2026-10-05-milestone-8-solution-definition.md",
            "docs/research/m8-solution-alternatives.md",
            "docs/research/m8-synthetic-fixtures.md",
            "docs/research/m8-source-receipts.json",
        )
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)
        plan = (ROOT / paths[1]).read_text()
        for card in ("t_f1a8ee89", "t_19c877cb", "t_913965f7", "t_2bedc90a",
                     "t_a7974c61", "t_1f505e56", "t_4841a335", "t_f0b10ab9",
                     "t_002ae0a4", "t_c009385c", "t_bcedc3b0"):
            self.assertIn(card, plan)

    def test_optional_dependency_and_native_discovery(self):
        manifest = ast.literal_eval((ADDON / "__manifest__.py").read_text())
        self.assertEqual(manifest["depends"], ["project_agile"])
        self.assertEqual(manifest["license"], "LGPL-3")
        self.assertTrue(manifest["installable"])
        for path in manifest["data"]:
            self.assertTrue((ADDON / path).is_file(), path)
            if path.endswith(".xml"):
                ET.parse(ADDON / path)
        self.assertIn("from . import models", (ADDON / "__init__.py").read_text())
        self.assertIn("test_solution_lineage", (ADDON / "tests" / "__init__.py").read_text())
        self.assertFalse((ADDON / "controllers").exists())
        self.assertFalse((ADDON / "static").exists())
        for addon in (ROOT / "addons").glob("*/__manifest__.py"):
            if addon.parent.name == 'project_agile_solution_scrum':
                self.assertEqual(ast.literal_eval(addon.read_text())['depends'], ['project_agile_solution', 'project_scrum'])
            elif addon.parent != ADDON:
                self.assertNotIn("project_agile_solution", ast.literal_eval(addon.read_text())["depends"])

    def test_verifier_installs_solution_independently_and_in_all_lifecycles(self):
        script = (ROOT / "scripts" / "verify").read_text()
        modules = next(line.split("=", 1)[1].split(",") for line in script.splitlines() if line.startswith("MODULES="))
        tags = next(line.split("=", 1)[1].split(",") for line in script.splitlines() if line.startswith("TEST_TAGS="))
        self.assertIn("project_agile_solution", modules)
        self.assertIn("/project_agile_solution", tags)
        self.assertIn('--init project_agile_solution --test-enable --test-tags /project_agile_solution', script)
        self.assertIn('--update "$MODULES" --test-enable --test-tags "$TEST_TAGS"', script)
        self.assertLess(script.index("uninstall_module project_agile_solution"), script.index("uninstall_module project_agile\n"))
        self.assertIn("solution_source_probe.py", script)

    def test_fixture_keys_scope_and_exact_revision_references_are_consistent(self):
        data = json.loads((ADDON / "tests" / "fixtures" / "synthetic_scenarios.json").read_text())
        self.assertTrue(data["synthetic"])
        self.assertEqual(data["schema_version"], 1)
        scenarios = data["scenarios"]
        self.assertEqual({item["id"] for item in scenarios}, {"portal", "integration", "internal"})
        self.assertEqual(len(scenarios), 3)
        for scenario in scenarios:
            self._check_scenario(scenario)
        portal, integration, internal = scenarios
        self.assertIn("Delegated submission", portal["excluded"])
        self.assertEqual(portal["trace"]["explicit_acceptance"]["status"], "expected_fixture_event_not_executed")
        self.assertIsNone(integration["questions"][0]["resolution"])
        self.assertTrue(integration["reviewed_scope_revision"]["requires_separate_sow_and_spec_approval"])
        self.assertFalse(internal["sow"])
        self.assertEqual(internal["tasks"][-1]["requirement_revisions"], [])
        self.assertTrue(internal["tasks"][-1]["maintenance_reason"])

    def _check_scenario(self, scenario):
        self.assertTrue(scenario["project_name"].startswith("SYNTHETIC"))
        self.assertTrue(scenario["weaknesses"])
        requirements = scenario["requirements"]
        keys = {item["key"] for item in requirements}
        revisions = {f'{item["key"]}@{item["revision"]}' for item in requirements}
        self.assertEqual(len(keys), len(requirements))
        self.assertEqual({item["type"] for item in requirements}, {"fr", "nfr"})
        for requirement in requirements:
            for field in ("text", "rationale", "priority", "verification", "audience"):
                self.assertTrue(requirement[field], field)
        for context in scenario["questions"] + scenario["decisions"] + [scenario["deliverable"]]:
            self.assertTrue(set(context["requirements"]) <= keys)
        for task in scenario["tasks"]:
            self.assertTrue(set(task["requirement_revisions"]) <= revisions)
        task_keys = {task["key"] for task in scenario["tasks"]}
        self.assertEqual(len(task_keys), len(scenario["tasks"]))
        for question in scenario["questions"]:
            self.assertTrue(question["owner_role"])
            self.assertTrue(question["planning_significance"])
            if question.get("spike_task"):
                self.assertIn(question["spike_task"], task_keys)

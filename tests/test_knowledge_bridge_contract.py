"""Static guard for the Knowledge bridge's fail-closed planning boundary."""

import ast
from pathlib import Path
import unittest


class TestKnowledgeBridgeContract(unittest.TestCase):
    """Ensure Community evidence is not misrepresented as Enterprise API proof."""

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.adr = (self.root / "docs" / "adrs" / "006-knowledge-relationship-model.md").read_text()
        self.plan = (
            self.root / "docs" / "plans" / "2026-09-26-project-agile-knowledge.md"
        ).read_text()

    def test_adr_requires_a_lawful_exact_version_fixture(self):
        self.assertIn("Blocked — architecture contract accepted", self.adr)
        self.assertIn("## `needs_input`", self.adr)
        self.assertIn("lawfully licensed Odoo 19 Enterprise", self.adr)
        self.assertIn("docs/research/odoo-19-knowledge-fixture.md", self.adr)
        self.assertIn("No bridge code, manifest dependency, XML data", self.adr)

    def test_contract_keeps_core_modules_knowledge_free(self):
        for module in ("project_agile", "project_scrum", "project_scrum_analytics"):
            manifest_path = self.root / "addons" / module / "__manifest__.py"
            manifest = ast.literal_eval(manifest_path.read_text())
            self.assertNotIn("knowledge", manifest["depends"])

        self.assertIn("`project_agile` remains independent of Knowledge and Scrum.", self.adr)
        self.assertIn("`project_scrum_knowledge` bridge", self.adr)

    def test_plan_separates_community_regression_from_enterprise_proof(self):
        self.assertIn("Community image is a regression boundary only", self.plan)
        self.assertIn("TDD implementation slices after the gate passes", self.plan)
        self.assertIn("`./scripts/verify`", self.plan)
        self.assertIn("Install, upgrade, uninstall/reinstall, and Community regression", self.plan)
        self.assertIn("no assets directory and no OWL component", self.plan)

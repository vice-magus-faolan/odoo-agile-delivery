"""Static contract for the pinned OCA Document Page verification surface."""

import ast
from pathlib import Path
import unittest


class TestOcaDocumentPageContract(unittest.TestCase):
    """Keep the optional OCA bridge explicit without widening the Community gate."""

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.fixture = (self.root / "docs" / "research" / "odoo-19-oca-document-page-fixture.md").read_text()
        self.compose = (self.root / "compose.oca-document-page.yaml").read_text()
        self.verify = (self.root / "scripts" / "verify-oca-document-page").read_text()

    def test_bridge_is_agpl_and_depends_only_on_selected_oca_project_api(self):
        module = self.root / "addons" / "project_agile_document_page"
        manifest = ast.literal_eval((module / "__manifest__.py").read_text())
        self.assertEqual(manifest["license"], "AGPL-3")
        self.assertEqual(manifest["depends"], ["project_agile", "document_page_project"])
        self.assertFalse((module / "static").exists())
        self.assertIn("never deletes or reparents", (module / "README.md").read_text())

    def test_fixture_exercises_bridge_without_widening_community_gate(self):
        self.assertIn("project_agile_document_page", self.verify)
        self.assertIn("project_agile", self.verify)
        self.assertIn("tmpfs", self.compose)
        self.assertIn("/mnt/extra-addons:ro", self.compose)
        self.assertNotIn("ports:", self.compose)
        community_verify = (self.root / "scripts" / "verify").read_text()
        self.assertIn("MODULES=project_agile,project_scrum,project_scrum_analytics", community_verify)
        self.assertNotIn("project_agile_document_page", community_verify)
        self.assertIn("AGPL-3", self.fixture)

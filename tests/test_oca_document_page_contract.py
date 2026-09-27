"""Static contract for the pinned OCA Document Page verification surface."""

import ast
from pathlib import Path
import unittest


class TestOcaDocumentPageContract(unittest.TestCase):
    """Keep the OCA fixture explicit without widening the Community gate."""

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.adr = (self.root / "docs" / "adrs" / "006-knowledge-relationship-model.md").read_text()
        self.plan = (
            self.root / "docs" / "plans" / "2026-09-26-project-agile-knowledge.md"
        ).read_text()
        self.fixture = (
            self.root / "docs" / "research" / "odoo-19-oca-document-page-fixture.md"
        ).read_text()
        self.compose = (self.root / "compose.oca-document-page.yaml").read_text()
        self.verify = (self.root / "scripts" / "verify-oca-document-page").read_text()

    def test_contract_selects_pinned_oca_document_page_not_enterprise_knowledge(self):
        for document in (self.adr, self.plan):
            self.assertIn("OCA Document Page", document)
            self.assertIn("e4a12c0c99866a5850840941d6f7ae3b3b27280d", document)
            self.assertIn("AGPL-3", document)
            self.assertIn("deferred alternative", document)
            self.assertIn("not API-compatible", document)

        self.assertNotIn("`needs_input`", self.adr)
        self.assertNotIn("Enterprise-only", self.plan)

    def test_fixture_pins_sources_and_records_runtime_contract(self):
        required = (
            "odoo@sha256:144175ec0039d52daff1d79f7e51c9281ca3c98b96c830feb49d09764a9f5d7c",
            "postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24",
            "document_knowledge",
            "document_page",
            "document_page_project",
            "document.page",
            "document.page.history",
            "document_knowledge.group_document_user",
            "document_page.group_document_editor",
            "document_page.group_document_manager",
            "document_page_project.action_document_page_projects",
            "company_id",
            "parent_id",
            "history_ids",
            "template",
            "PR #641",
            "b790965e66a008da4421a8763c489037bbb8a43a",
            "unmerged",
        )
        for value in required:
            self.assertIn(value, self.fixture)

        self.assertIn("tmpfs", self.compose)
        self.assertIn("/mnt/extra-addons:ro", self.compose)
        self.assertNotIn("ports:", self.compose)
        self.assertIn("--init \"$MODULES\"", self.verify)
        self.assertIn("--update \"$MODULES\"", self.verify)
        self.assertIn("uninstall_module document_page_project", self.verify)
        self.assertIn("uninstall_module document_page", self.verify)
        self.assertIn("uninstall_module document_knowledge", self.verify)
        self.assertIn('-d "$DATABASE_INSTALL"', self.verify)
        self.assertIn('-d "$DATABASE_REINSTALL"', self.verify)

    def test_community_gate_remains_community_only(self):
        community_verify = (self.root / "scripts" / "verify").read_text()
        self.assertIn(
            "MODULES=project_agile,project_scrum,project_scrum_analytics",
            community_verify,
        )
        self.assertNotIn("document_page", community_verify)
        self.assertNotIn("document_knowledge", community_verify)

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

"""Static guard for the OCA Document Page Milestone 4 contract."""

import ast
import unittest
from pathlib import Path


class TestKnowledgeBridgeContract(unittest.TestCase):
    """Keep Community modules independent while pinning the OCA backend contract."""

    # Plain unittest.TestCase has no Odoo transaction setup to chain.
    def setUp(self):  # pylint: disable=method-required-super
        self.root = Path(__file__).resolve().parents[1]
        self.adr = (
            self.root / "docs" / "adrs" / "006-knowledge-relationship-model.md"
        ).read_text()
        self.plan = (
            self.root / "docs" / "plans" / "2026-09-26-project-agile-knowledge.md"
        ).read_text()
        self.fixture = (
            self.root / "docs" / "research" / "odoo-19-oca-document-page-fixture.md"
        ).read_text()

    def test_adr_selects_oca_document_page_and_defers_enterprise(self):
        self.assertIn("Accepted — supersedes", self.adr)
        self.assertIn("OCA Document Page", self.adr)
        self.assertIn("e4a12c0c99866a5850840941d6f7ae3b3b27280d", self.adr)
        self.assertIn("deferred alternative backend", self.adr)
        self.assertIn("not API-compatible", self.adr)
        self.assertNotIn("## `needs_input`", self.adr)

    def test_contract_keeps_community_modules_document_free(self):
        document_modules = {
            "document_knowledge",
            "document_page",
            "document_page_project",
        }
        for module in ("project_agile", "project_scrum", "project_scrum_analytics"):
            manifest_path = self.root / "addons" / module / "__manifest__.py"
            manifest = ast.literal_eval(manifest_path.read_text())
            self.assertFalse(document_modules.intersection(manifest["depends"]))

        self.assertIn(
            "`project_agile`, `project_scrum`, and `project_scrum_analytics`", self.adr
        )
        self.assertIn("remain Community-only", self.adr)

    def test_plan_requires_the_separate_pinned_fixture_and_pr_gate(self):
        self.assertIn("`./scripts/verify-oca-document-page`", self.plan)
        self.assertIn("`./scripts/verify`", self.plan)
        self.assertIn("OCA PR #641", self.plan)
        self.assertIn("open and unmerged", self.plan)
        self.assertIn(
            "not vendored, copied, or used as a production dependency",
            " ".join(self.plan.split()),
        )
        self.assertIn("AGPL-3", self.fixture)

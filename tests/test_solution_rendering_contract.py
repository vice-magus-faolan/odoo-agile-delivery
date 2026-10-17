"""Structural discovery guards; actual native report/security proof is separate."""

import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addons/project_agile_solution"


class TestSolutionRenderingContract(unittest.TestCase):
    def test_native_reports_disable_attachment_cache_and_escape_all_output(self):
        tree = ET.parse(ADDON / "report/solution_reports.xml")
        reports = tree.findall(".//record[@model='ir.actions.report']")
        self.assertEqual(len(reports), 2)
        for report in reports:
            for name in ("attachment_use", "attachment"):
                field = report.find(f"field[@name='{name}']")
                assert field is not None
                self.assertEqual(field.get("eval"), "False")
            report_type = report.find("field[@name='report_type']")
            assert report_type is not None
            self.assertEqual(report_type.text, "qweb-html")
        self.assertFalse(tree.findall(".//*[@t-raw]"))
        self.assertFalse((ADDON / "controllers").exists())
        source = (ADDON / "models/solution_projection.py").read_text()
        self.assertIn("revision.action_projection(self._audience)", source)
        self.assertNotIn("Markup(", source)
        self.assertNotIn("requests.", source)

    def test_acceptance_and_preview_are_imported_with_global_authority_rules(self):
        imported = (ADDON / "models/__init__.py").read_text()
        for name in ("solution_projection", "solution_acceptance", "solution_coverage"):
            self.assertIn("from . import " + name, imported)
        rules = ET.parse(ADDON / "security/project_agile_solution_rules.xml")
        for rule_id in (
            "acceptance_project_rule",
            "acceptance_company_rule",
            "preview_revision_rule",
        ):
            rule = rules.find(f".//record[@id='{rule_id}']")
            assert rule is not None
            self.assertIsNone(rule.find("field[@name='groups']"))
        for filename in (
            "solution_projection.py",
            "solution_acceptance.py",
            "solution_coverage.py",
        ):
            for node in ast.walk(ast.parse((ADDON / "models" / filename).read_text())):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, {"commit", "rollback"})

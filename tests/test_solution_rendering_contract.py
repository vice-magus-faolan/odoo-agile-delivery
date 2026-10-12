"""Structural discovery guards; actual native report/security proof is separate."""

import ast
import importlib.util
import subprocess
import sys
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

    def test_rendering_and_browser_discovery_cannot_be_omitted(self):
        script = ROOT / "scripts/check_solution_test_run.py"
        spec = importlib.util.spec_from_file_location("rendering_discovery", script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suites = (
            ("TestSolutionBaseline", module.expected_methods),
            ("TestSolutionRequirements", module.expected_requirement_methods),
            ("TestSolutionTaskTrace", module.expected_trace_methods),
            ("TestSolutionRendering", module.expected_rendering_methods),
            ("TestSolutionRenderTour", module.expected_render_tour_methods),
        )
        text = "".join(
            f"Starting {name}.{method}\n"
            for name, function in suites[:3]
            for method in function()
        )
        command = [
            sys.executable,
            str(script),
            "--init",
            "project_agile_solution",
            "--test-enable",
        ]
        missing_render = subprocess.run(
            command, input=text, text=True, capture_output=True
        )
        self.assertNotEqual(missing_render.returncode, 0)
        self.assertIn("RENDERING tests not actually discovered", missing_render.stderr)
        text += "".join(
            f"Starting TestSolutionRendering.{method}\n"
            for method in module.expected_rendering_methods()
        )
        missing_browser = subprocess.run(
            command, input=text, text=True, capture_output=True
        )
        self.assertNotEqual(missing_browser.returncode, 0)
        self.assertIn(
            "RENDER_TOUR tests not actually discovered", missing_browser.stderr
        )
        text += "".join(
            f"Starting TestSolutionRenderTour.{method}\n"
            for method in module.expected_render_tour_methods()
        )
        text = "".join(
            f"Starting {name}.{method}\n"
            for name, (_, methods) in module.declared_suites().items()
            for method in methods
        )
        text += "0 failed, 0 error(s) of 113 tests when loading database\n"
        self.assertEqual(
            subprocess.run(
                command, input=text, text=True, capture_output=True
            ).returncode,
            0,
        )

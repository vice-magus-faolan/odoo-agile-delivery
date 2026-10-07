"""Structural guards for cumulative M8 proof, not substitutes for native tests."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestSolutionHardeningContract(unittest.TestCase):
    def test_optional_lifecycles_verify_persisted_history_and_native_work(self):
        verify = (ROOT / 'scripts/verify').read_text()
        for phase in ('seed_core', 'check_core', 'removed_core', 'reinstalled_core',
                      'seed_bridge', 'check_bridge', 'removed_bridge', 'reinstalled_bridge'):
            self.assertIn('solution_lifecycle ' + phase, verify)
        self.assertIn('--update project_agile_solution --test-enable', verify)
        self.assertIn('--update project_agile_solution,project_agile_solution_scrum --test-enable', verify)
        probe = (ROOT / 'scripts/solution_lifecycle_probe.py').read_text()
        self.assertIn("assert env.cr.dbname == DATABASE", probe)
        self.assertIn("DATABASE = 'odoo_agile_verify_install'", probe)
        for proof in ('snapshot_json ==', 'action_confirm()', 'event_values', 'not_available', 'native_values(task) =='):
            self.assertIn(proof, probe)

    def test_cardinality_deny_check_remains_bounded(self):
        tree = ast.parse((ROOT / 'addons/project_agile_solution/models/solution_coverage.py').read_text())
        helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'complete_rows')
        counts = [node for node in ast.walk(helper) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and node.func.attr == 'search_count']
        self.assertEqual(len(counts), 1)
        self.assertEqual([keyword.arg for keyword in counts[0].keywords], ['limit'])

    def test_native_http_rpc_negatives_are_imported_and_discovered(self):
        directory = ROOT / 'addons/project_agile_solution/tests'
        self.assertIn('from . import test_solution_hardening', (directory / '__init__.py').read_text())
        tour = (directory / 'test_solution_render_tour.py').read_text()
        for boundary in ('/web/dataset/call_kw', 'export_data', 'action_projection', 'action_coverage',
                         'action_approve', 'solution_trusted', 'odoo.exceptions.AccessError'):
            self.assertIn(boundary, tour)
        self.assertTrue((ROOT / 'docs/implementation/m8-hardening-matrix.md').is_file())

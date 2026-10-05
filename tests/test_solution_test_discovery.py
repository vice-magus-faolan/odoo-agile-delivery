"""Unit checks for discovery gate behavior, not substitute native Odoo proof."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_solution_test_run.py'


class TestSolutionNativeDiscoveryGate(unittest.TestCase):
    def _run(self, text, args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=text, capture_output=True, text=True, check=False)

    def test_zero_baseline_discovery_is_rejected(self):
        result = self._run('Odoo exited successfully but no target tests ran.\n', ['--init', 'project_agile_solution', '--test-enable'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not actually discovered', result.stderr)

    def test_missing_single_test_is_rejected(self):
        methods = self._methods()
        text = ''.join(f'Starting TestSolutionBaseline.{name}\n' for name in sorted(methods)[1:])
        self.assertNotEqual(self._run(text, ['--update', 'project_agile_solution', '--test-enable']).returncode, 0)

    def test_exact_parser_fixture_streams_all_declared_methods(self):
        text = ''.join(f'Starting TestSolutionBaseline.{name}\n' for name in sorted(self._methods()))
        result = self._run(text, ['--init', 'project_agile_solution', '--test-enable'])
        self.assertEqual(result.returncode, 0)
        self.assertIn('M8_BASELINE_NATIVE_DISCOVERY_OK', result.stdout)
        self.assertIn(text, result.stdout)

    def test_other_addons_and_schema_only_setup_do_not_require_tests(self):
        for args in (['--init', 'project_agile_solution'], ['--init', 'project_agile_git_automation', '--test-enable']):
            self.assertEqual(self._run('Setup only\n', args).returncode, 0)

    def _methods(self):
        spec = importlib.util.spec_from_file_location('solution_discovery_gate', SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        methods = module.expected_methods()
        self.assertTrue(methods)
        return methods

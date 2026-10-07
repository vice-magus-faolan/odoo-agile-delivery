"""Static boundary/discovery checks supplement, never replace native execution."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestTaskTraceContract(unittest.TestCase):
    def _text(self, path):
        return (ROOT / path).read_text()

    def test_optional_bridge_and_native_event_return_seam(self):
        core = ast.literal_eval(self._text('addons/project_agile_solution/__manifest__.py'))
        bridge = ast.literal_eval(self._text('addons/project_agile_solution_scrum/__manifest__.py'))
        self.assertEqual(core['depends'], ['project_agile'])
        self.assertEqual(bridge['depends'], ['project_agile_solution', 'project_scrum'])
        self.assertEqual(bridge['license'], core['license'])
        self.assertIn('return self.env["project.sprint.scope.event"].sudo().create(values)', self._text('addons/project_scrum/models/project_sprint.py'))
        capture = self._text('addons/project_agile_solution_scrum/models/sprint_context.py')
        self.assertIn('super()._append_scope_events', capture)
        self.assertNotIn('def action_start', capture)
        self.assertNotIn('def action_close', capture)

    def test_m7_finite_task_source_pins_match_optional_extensions(self):
        tree = ast.parse(self._text('addons/project_agile_git_automation/models/policy_write_profile.py'))
        sources = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'SOURCES' for target in node.targets))
        for name in ('addons/project_agile_solution/models/project_task_trace.py', 'addons/project_agile_solution_scrum/models/project_task.py'):
            self.assertEqual(sources[name], hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
        self.assertNotIn('*', ''.join(sources))

    def test_core_and_bridge_have_real_imported_test_packages(self):
        for addon, test in (('project_agile_solution', 'test_solution_task_trace'), ('project_agile_solution_scrum', 'test_sprint_context')):
            self.assertIn('from . import '+test, self._text(f'addons/{addon}/tests/__init__.py'))
            self.assertTrue((ROOT/f'addons/{addon}/tests/{test}.py').is_file())
        self.assertIn('CREATE', self._text('addons/project_agile_solution/models/solution_task_intent.py').upper())

    def test_canonical_gate_preserves_core_and_bridge_lifetimes_and_races(self):
        text = self._text('scripts/verify')
        self.assertIn('--init project_agile_solution --test-enable', text)
        self.assertIn('--init project_agile_solution_scrum --test-enable', text)
        self.assertIn('solution_scrum_probe.py', text)
        self.assertLess(text.index('uninstall_module project_agile_solution_scrum\n'), text.index('uninstall_module project_agile_solution\n'))
        self.assertIn('run_task_probe(env)', self._text('scripts/solution_source_probe.py'))
        self.assertIn("('relink', 'close')", self._text('scripts/solution_scrum_probe.py'))

    def test_production_sources_never_commit_or_rollback_transactions(self):
        for path in ('addons/project_agile_solution/models/solution_task_intent.py', 'addons/project_agile_solution/models/solution_task_link.py',
                     'addons/project_agile_solution/models/solution_task_access.py', 'addons/project_agile_solution_scrum/models/sprint_context.py'):
            tree = ast.parse(self._text(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, {'commit', 'rollback'}, path)

    def test_missing_trace_or_scrum_native_discovery_is_not_a_pass(self):
        script = ROOT/'scripts/check_solution_test_run.py'
        spec = importlib.util.spec_from_file_location('m8_discovery', script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        text = ''.join(f'Starting {cls}.{name}\n' for cls, function in (
            ('TestSolutionBaseline', module.expected_methods), ('TestSolutionRequirements', module.expected_requirement_methods)) for name in function())
        args = [sys.executable, str(script), '--init', 'project_agile_solution_scrum', '--test-enable']
        result = subprocess.run(args, input=text, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('TASK_TRACE tests not actually discovered', result.stderr)
        text += ''.join(f'Starting TestSolutionTaskTrace.{name}\n' for name in module.expected_trace_methods())
        text += ''.join(f'Starting TestSolutionRendering.{name}\n' for name in module.expected_rendering_methods())
        text += ''.join(f'Starting TestSolutionRenderTour.{name}\n' for name in module.expected_render_tour_methods())
        result = subprocess.run(args, input=text, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SCRUM_CONTEXT tests not actually discovered', result.stderr)
        text += ''.join(f'Starting TestSolutionSprintContext.{name}\n' for name in module.expected_scrum_methods())
        text = ''.join(f'Starting {name}.{method}\n' for name, (_, methods) in module.declared_suites(
            ('project_agile_solution', 'project_agile_solution_scrum')).items() for method in methods)
        self.assertEqual(subprocess.run(args, input=text, text=True, capture_output=True).returncode, 0)

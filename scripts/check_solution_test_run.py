"""Stream native Odoo output and fail closed on missing solution test discovery."""
import ast
from pathlib import Path
import re
import sys


def expected_methods():
    """Require every locally declared baseline test, not inherited duplicates."""
    path = Path(__file__).resolve().parents[1] / 'addons/project_agile_solution/tests/test_solution_baseline.py'
    tree = ast.parse(path.read_text())
    return {node.name for cls in tree.body if isinstance(cls, ast.ClassDef) and cls.name == 'TestSolutionBaseline'
            for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}

def expected_requirement_methods():
    path = Path(__file__).resolve().parents[1] / 'addons/project_agile_solution/tests/test_solution_requirements.py'
    tree = ast.parse(path.read_text())
    return {node.name for cls in tree.body if isinstance(cls, ast.ClassDef) and cls.name == 'TestSolutionRequirements'
            for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}


def expected_trace_methods():
    return _declared_methods('project_agile_solution', 'test_solution_task_trace.py', 'TestSolutionTaskTrace')


def expected_scrum_methods():
    return _declared_methods('project_agile_solution_scrum', 'test_sprint_context.py', 'TestSolutionSprintContext')


def _declared_methods(addon, filename, classname):
    path = Path(__file__).resolve().parents[1] / 'addons' / addon / 'tests' / filename
    tree = ast.parse(path.read_text())
    return {node.name for cls in tree.body if isinstance(cls, ast.ClassDef) and cls.name == classname
            for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}


def main():
    args = sys.argv[1:]
    required = '--test-enable' in args and any('project_agile_solution' in arg for arg in args)
    suites = {
        'TestSolutionBaseline': ('baseline', expected_methods),
        'TestSolutionRequirements': ('requirement', expected_requirement_methods),
        'TestSolutionTaskTrace': ('TASK_TRACE', expected_trace_methods),
    }
    if any('project_agile_solution_scrum' in arg for arg in args):
        suites['TestSolutionSprintContext'] = ('SCRUM_CONTEXT', expected_scrum_methods)
    observed = {name: set() for name in suites}
    for line in sys.stdin:
        print(line, end='', flush=True)
        match = re.search(r'Starting (TestSolution\w+)\.(test_\w+)', line)
        if match and match.group(1) in observed:
            observed[match.group(1)].add(match.group(2))
    if required:
        for name, (label, expected) in suites.items():
            if not _check_discovery(label, expected(), observed[name]):
                return 1
    return 0


def _check_discovery(label, expected, observed):
    missing = expected - observed
    if not expected or missing:
        print(f'M8 {label} tests not actually discovered: ' + ', '.join(sorted(missing)), file=sys.stderr)
        return False
    marker = {'baseline': 'M8_BASELINE_NATIVE_DISCOVERY_OK', 'requirement': 'M8_REQUIREMENTS_NATIVE_DISCOVERY_OK'}.get(label, f'M8_{label}_NATIVE_DISCOVERY_OK')
    print(f'{marker} methods={len(observed)}', flush=True)
    return True


if __name__ == '__main__':
    raise SystemExit(main())

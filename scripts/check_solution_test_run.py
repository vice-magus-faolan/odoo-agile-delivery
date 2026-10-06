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


def main():
    args = sys.argv[1:]
    required = '--test-enable' in args and any('project_agile_solution' in arg for arg in args)
    observed = set()
    requirements_observed = set()
    for line in sys.stdin:
        print(line, end='', flush=True)
        match = re.search(r'Starting TestSolutionBaseline\.(test_\w+)', line)
        if match:
            observed.add(match.group(1))
        match = re.search(r'Starting TestSolutionRequirements\.(test_\w+)', line)
        if match:
            requirements_observed.add(match.group(1))
    if required:
        expected = expected_methods()
        missing = expected - observed
        if not expected or missing:
            print('M8 baseline tests not actually discovered: ' + ', '.join(sorted(missing)), file=sys.stderr)
            return 1
        print(f'M8_BASELINE_NATIVE_DISCOVERY_OK methods={len(observed)}', flush=True)
        expected_requirements = expected_requirement_methods()
        missing_requirements = expected_requirements - requirements_observed
        if not expected_requirements or missing_requirements:
            print('M8 requirement tests not actually discovered: ' + ', '.join(sorted(missing_requirements)), file=sys.stderr)
            return 1
        print(f'M8_REQUIREMENTS_NATIVE_DISCOVERY_OK methods={len(requirements_observed)}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

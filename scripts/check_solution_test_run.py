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


def expected_rendering_methods():
    return _declared_methods('project_agile_solution', 'test_solution_rendering.py', 'TestSolutionRendering')


def expected_render_tour_methods():
    return _declared_methods('project_agile_solution', 'test_solution_render_tour.py', 'TestSolutionRenderTour')


def _declared_methods(addon, filename, classname):
    path = Path(__file__).resolve().parents[1] / 'addons' / addon / 'tests' / filename
    tree = ast.parse(path.read_text())
    return {node.name for cls in tree.body if isinstance(cls, ast.ClassDef) and cls.name == classname
            for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}


LABELS = {
    'TestSolutionLineage': 'LINEAGE', 'TestSolutionBaseline': 'baseline',
    'TestSolutionRequirements': 'requirement', 'TestSolutionTaskTrace': 'TASK_TRACE',
    'TestSolutionRendering': 'RENDERING', 'TestSolutionRenderTour': 'RENDER_TOUR',
    'TestSolutionSprintContext': 'SCRUM_CONTEXT',
    'TestSolutionHardening': 'HARDENING',
}


def declared_suites(addons=('project_agile_solution',), root=None):
    """Derive required native methods from source and require package imports.

    Inherited duplicate execution is not discovery of the declaring class.
    An added test file must be imported; an empty/missing package cannot pass.
    This AST check never imports Odoo or substitutes for native execution.
    """
    root = root or Path(__file__).resolve().parents[1] / 'addons'
    suites = {}
    for addon in addons:
        for path in imported_test_files(root / addon / 'tests'):
            for name, methods in file_suites(path).items():
                if name in suites:
                    raise ValueError(f'Ambiguous native test class: {name}')
                suites[name] = (LABELS.get(name, name), methods)
    if not suites:
        raise ValueError('No declared native test methods')
    return suites


def imported_test_files(directory):
    imports = ast.parse((directory / '__init__.py').read_text())
    imported = {alias.name for node in imports.body if isinstance(node, ast.ImportFrom)
                and node.level == 1 and node.module is None for alias in node.names}
    files = sorted(directory.glob('test_*.py'))
    if not files:
        raise ValueError(f'No native test files in {directory}')
    for path in files:
        if path.stem not in imported:
            raise ValueError(f'Native test file is not imported: {path}')
    return files


def file_suites(path):
    suites = {}
    for cls in ast.parse(path.read_text()).body:
        if isinstance(cls, ast.ClassDef):
            methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)
                       and node.name.startswith('test_')}
            if methods:
                suites[cls.name] = methods
    return suites


def native_result(line):
    """Interpret an actual Odoo result summary, not a test-start marker."""
    summary = re.search(r'(\d+) failed, (\d+) error\(s\) of (\d+) tests when loading database', line)
    if not summary:
        return False, False
    failures, errors, tests = map(int, summary.groups())
    return bool(failures or errors), failures == errors == 0 and tests > 0


def stream_results(suites):
    """Stream intact output, retaining test identity and native failure summaries."""
    observed = {name: set() for name in suites}
    skipped = {name: set() for name in suites}
    failed = False
    successful_summary = False
    for line in sys.stdin:
        print(line, end='', flush=True)
        match = re.search(r'Starting (Test\w+)\.(test_\w+)', line)
        if match and match.group(1) in observed:
            observed[match.group(1)].add(match.group(2))
        skip = re.search(r'skipped (?:Subtest )?(Test\w+)\.(test_\w+)\b', line)
        if skip and skip.group(1) in skipped:
            skipped[skip.group(1)].add(skip.group(2))
        line_failed, line_successful = native_result(line)
        failed = failed or line_failed
        successful_summary = successful_summary or line_successful
    for name, methods in skipped.items():
        if methods:
            observed[name] -= methods
            print(f'Required native test was skipped: {name}.' + ', '.join(sorted(methods)), file=sys.stderr)
    return observed, failed, successful_summary


def main():
    args = sys.argv[1:]
    required = '--test-enable' in args and any('project_agile_solution' in arg for arg in args)
    addons = ['project_agile_solution']
    if any('project_agile_solution_scrum' in arg for arg in args):
        addons.append('project_agile_solution_scrum')
    try:
        suites = declared_suites(addons) if required else {}
    except (OSError, ValueError, SyntaxError) as error:
        print(f'M8 native discovery contract failed: {error}', file=sys.stderr)
        return 1
    observed, failed, successful_summary = stream_results(suites)
    complete = True
    for name, (label, expected) in suites.items():
        complete = _check_discovery(label, expected, observed[name]) and complete
    if failed:
        print('Odoo reported a native test failure; starting tests is not passing them.', file=sys.stderr)
    if required and not successful_summary:
        print('Missing successful native result summary for selected M8 tests.', file=sys.stderr)
        complete = False
    return 0 if complete and not failed else 1


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

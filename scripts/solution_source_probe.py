"""Read-only exact-runtime API discovery and owned disposable baseline race proof."""
from pathlib import Path
import hashlib
import os

# Only reviewed public scripts actually used by this lane; never settings,
# credentials or a recursively selected path. This runs as the real Odoo user.
public_scripts = ('solution_source_probe.py', 'solution_scrum_probe.py', 'solution_lifecycle_probe.py',
                  'git_policy_concurrency_probe.py', 'git_policy_concurrency_worker.py',
                  'github_association_concurrency_probe.py', 'github_association_concurrency_worker.py')
assert os.geteuid() != 0, 'Readability proof must not run as root'
for name in public_scripts:
    path = Path('/mnt/policy-tests') / name
    assert path.is_file() and os.access(path, os.R_OK), f'Non-root public script unreadable: {name}'
    print('M8_PUBLIC_SCRIPT_READABLE', name, hashlib.sha256(path.read_bytes()).hexdigest())
print('M8_PUBLIC_NONROOT_READABILITY_OK uid=' + str(os.geteuid()), flush=True)

root = Path("/usr/lib/python3/dist-packages/odoo")
files = (
    "addons/project/security/project_security.xml",
    "addons/project/models/project_project.py",
    "addons/project/models/project_task.py",
    "orm/models.py",
    "orm/domains.py",
    "addons/base/models/ir_actions_report.py",
    "addons/base/models/ir_sequence.py",
)
for name in files:
    path = root / name
    print(name, hashlib.sha256(path.read_bytes()).hexdigest())
    if name.endswith("project_security.xml"):
        print(path.read_text())
    else:
        lines = path.read_text().splitlines()
        tokens = ("def check_access(", "def _filtered_access(", "def _search(", "def _render_qweb_html(", "def _get_report_values(", "def create(", "def write(", "company_id =", "privacy_visibility =", "parent_id =", "depend_on_ids =", "def _check_company(", "def next_by_id(")
        for index, line in enumerate(lines):
            if any(token in line for token in tokens):
                print("\n".join(f"{pos+1}: {lines[pos]}" for pos in range(max(index-1, 0), min(index+30, len(lines)))))
print((root / "release.py").read_text())
print("M8_NATIVE_SOURCE_PROBE_OK")

# Fail closed if Odoo silently ignored the addon or the baseline schema.
solution = env["ir.module.module"].search([("name", "=", "project_agile_solution")])
assert solution.state == "installed", "Solution addon not actually installed"
for model in ("project.agile.solution", "project.agile.solution.document", "project.agile.solution.revision", "project.agile.solution.section", "project.agile.solution.template"):
    assert model in env.registry, f"Solution model not registered: {model}"
assert env.ref("project_agile_solution.action_solution_lineage"), "Solution views not loaded"
assert env.ref("project_agile_solution.action_solution_document"), "Document views not loaded"
for model in ('project.agile.requirement', 'project.agile.requirement.revision', 'project.agile.solution.context', 'project.agile.solution.context.revision'):
    assert model in env.registry, f"Intent model not registered: {model}"
assert env.ref('project_agile_solution.action_requirement'), 'Requirement views not loaded'
assert env.ref('project_agile_solution.template_sow_skeleton'), 'Reusable SOW skeleton not loaded'
for name in ("project_scrum", "project_agile_git", "sale", "document_page", "knowledge"):
    module = env["ir.module.module"].search([("name", "=", name)])
    assert not module or module.state != "installed", f"Unexpected core dependency: {name}"
print("M8_ISOLATED_SOLUTION_INSTALL_OK")

# This shell owns a disposable fixture DB: explicit commits are test-only.
from odoo.addons.project_agile_solution.tests.baseline_concurrency import run_probe
run_probe(env)
from odoo.addons.project_agile_solution.tests.requirement_concurrency import run_probe as run_content_probe
run_content_probe(env)
from odoo.addons.project_agile_solution.tests.task_concurrency import run_probe as run_task_probe
run_task_probe(env)

"""Read-only exact-runtime API discovery; run in the disposable verifier image."""
from pathlib import Path
import hashlib

root = Path("/usr/lib/python3/dist-packages/odoo")
files = (
    "addons/project/security/project_security.xml",
    "addons/project/models/project_project.py",
    "addons/project/models/project_task.py",
    "orm/models.py",
    "orm/domains.py",
    "addons/base/models/ir_actions_report.py",
)
for name in files:
    path = root / name
    print(name, hashlib.sha256(path.read_bytes()).hexdigest())
    if name.endswith("project_security.xml"):
        print(path.read_text())
    else:
        lines = path.read_text().splitlines()
        tokens = ("def check_access(", "def _filtered_access(", "def _search(", "def _render_qweb_html(", "def _get_report_values(", "def create(", "def write(", "company_id =", "privacy_visibility =", "parent_id =", "depend_on_ids =", "def _check_company(")
        for index, line in enumerate(lines):
            if any(token in line for token in tokens):
                print("\n".join(f"{pos+1}: {lines[pos]}" for pos in range(max(index-1, 0), min(index+30, len(lines)))))
print((root / "release.py").read_text())
print("M8_NATIVE_SOURCE_PROBE_OK")

# Canonical isolated install must fail closed if Odoo ignored the addon entirely.
solution = env["ir.module.module"].search([("name", "=", "project_agile_solution")])
assert solution.state == "installed", "Solution addon not actually installed"
assert "project.agile.solution" in env.registry, "Solution model not registered"
assert env.ref("project_agile_solution.action_solution_lineage"), "Solution views not loaded"
for name in ("project_scrum", "project_agile_git", "sale", "document_page", "knowledge"):
    module = env["ir.module.module"].search([("name", "=", name)])
    assert not module or module.state != "installed", f"Unexpected core dependency: {name}"
print("M8_ISOLATED_SOLUTION_INSTALL_OK")

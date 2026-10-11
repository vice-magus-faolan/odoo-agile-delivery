"""Assert ordinary installed Scrum startup does not eagerly load its tests."""

import sys

from odoo.tools import config


module = env["ir.module.module"].search([("name", "=", "project_scrum")], limit=1)
print(f"Scrum module state: {module.state}; test_enable: {config['test_enable']}")
assert module.state == "installed", "Scrum must be installed before checking imports"
assert not config["test_enable"], "Import regression requires ordinary non-test startup"
prefix = "odoo.addons.project_scrum.tests"
loaded = sorted(
    name for name in sys.modules if name == prefix or name.startswith(prefix + ".")
)
assert not loaded, f"Production startup imported Scrum tests: {loaded}"
print("Ordinary Scrum startup passed: no Scrum test package or descendants loaded.")

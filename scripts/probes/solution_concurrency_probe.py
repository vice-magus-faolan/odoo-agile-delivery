"""Isolated optional dependencies and independent solution transaction races."""

import os
import sys
from pathlib import Path

sys.path.insert(0, "/mnt/policy-tests")

from baseline_concurrency import run_probe
from requirement_concurrency import run_probe as run_content_probe
from task_concurrency import run_probe as run_task_probe

assert os.geteuid() != 0, "Probes must execute as non-root Odoo"
for path in Path("/mnt/policy-tests").glob("*.py"):
    assert os.access(path, os.R_OK), f"Non-root public probe unreadable: {path.name}"

for name in (
    "project_scrum",
    "project_agile_git",
    "sale",
    "document_page",
    "knowledge",
):
    module = env["ir.module.module"].search([("name", "=", name)])
    assert not module or module.state != "installed", (
        f"Unexpected core dependency: {name}"
    )

run_probe(env)
run_content_probe(env)
run_task_probe(env)

# Execute one public planning mutation from a separate Odoo process and cursor.

import json
import os
from pathlib import Path
import time

from odoo.exceptions import AccessError, ValidationError


output_directory = Path("/mnt/planning-concurrency")
worker = os.environ["PLANNING_WORKER"]
scenario = json.loads((output_directory / "scenario.json").read_text())
(output_directory / f"{worker}.ready").write_text("ready\n")
deadline = time.monotonic() + 10
while not (output_directory / "start").exists():
    if time.monotonic() >= deadline:
        raise RuntimeError(f"{worker} did not receive a start signal")
    time.sleep(0.02)

reorder_first, reorder_second, reorder_third = scenario["reorder_task_ids"]
operations = {
    "assign": (
        "assign",
        [scenario["conflict_task_id"]],
        {"sprint_id": scenario["sprint_id"], "expected_versions": scenario["assign_return_versions"]},
    ),
    "return": (
        "return",
        [scenario["conflict_task_id"]],
        {"expected_versions": scenario["assign_return_versions"]},
    ),
    "reorder_first": (
        "reorder",
        [reorder_third],
        {
            "before_task_id": reorder_first,
            "expected_versions": {
                "tasks": {
                    str(reorder_third): scenario["reorder_versions"][str(reorder_third)],
                    str(reorder_first): scenario["reorder_versions"][str(reorder_first)],
                },
                "sprints": {},
            },
        },
    ),
    "reorder_second": (
        "reorder",
        [reorder_second],
        {
            "before_task_id": reorder_first,
            "expected_versions": {
                "tasks": {
                    str(reorder_second): scenario["reorder_versions"][str(reorder_second)],
                    str(reorder_first): scenario["reorder_versions"][str(reorder_first)],
                },
                "sprints": {},
            },
        },
    ),
}
operation, task_ids, options = operations[worker]
result = {"worker": worker}
try:
    env.cr.execute("SET LOCAL lock_timeout = '2s'")
    env.cr.execute("SET LOCAL statement_timeout = '10s'")
    env["project.project"].apply_agile_planning_change(
        scenario["project_id"], operation, task_ids, **options
    )
    env.cr.commit()
    result["outcome"] = "success"
except (AccessError, ValidationError) as error:
    env.cr.rollback()
    result.update({"outcome": "rejected", "error": str(error)})
except Exception as error:
    env.cr.rollback()
    result.update({"outcome": "failed", "error": f"{type(error).__name__}: {error}"})
(output_directory / f"{worker}.json").write_text(json.dumps(result, sort_keys=True))
if result["outcome"] == "failed":
    raise RuntimeError(result["error"])

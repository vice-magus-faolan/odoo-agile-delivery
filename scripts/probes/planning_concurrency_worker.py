# Execute one public planning mutation from a separate Odoo process and cursor.

import json
import os
import time
from pathlib import Path

from odoo.exceptions import AccessError, ValidationError

output_directory = Path(os.environ["PLANNING_DIRECTORY"])
worker = os.environ["PLANNING_WORKER"]
scenario = json.loads((output_directory / "scenario.json").read_text())
reorder_first, reorder_second, reorder_third = scenario["reorder_task_ids"]
operations = {
    "assign": (
        "assign",
        [scenario["assign_task_id"]],
        {
            "sprint_id": scenario["sprint_id"],
            "expected_versions": {
                "tasks": {
                    str(scenario["assign_task_id"]): scenario["assign_return_versions"][
                        "tasks"
                    ][str(scenario["assign_task_id"])]
                },
                "sprints": scenario["assign_return_versions"]["sprints"],
            },
        },
    ),
    "return": (
        "return",
        [scenario["return_task_id"]],
        {
            "expected_versions": {
                "tasks": {
                    str(scenario["return_task_id"]): scenario["assign_return_versions"][
                        "tasks"
                    ][str(scenario["return_task_id"])]
                },
                "sprints": scenario["assign_return_versions"]["sprints"],
            }
        },
    ),
    "reorder_first": (
        "reorder",
        [reorder_third],
        {
            "before_task_id": reorder_first,
            "expected_versions": {
                "tasks": {
                    str(reorder_third): scenario["reorder_versions"][
                        str(reorder_third)
                    ],
                    str(reorder_first): scenario["reorder_versions"][
                        str(reorder_first)
                    ],
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
                    str(reorder_second): scenario["reorder_versions"][
                        str(reorder_second)
                    ],
                    str(reorder_first): scenario["reorder_versions"][
                        str(reorder_first)
                    ],
                },
                "sprints": {},
            },
        },
    ),
}
operation, task_ids, options = operations[worker]
# Read the actual project and frozen records before releasing either action.
# These ORM reads establish both repeatable-read snapshots without a shared write.
planning = env["project.project"]
project = planning._get_available_agile_planning_project(scenario["project_id"])
assert project.agile_planning_backlog_revision >= 0
for task_id, version in options["expected_versions"]["tasks"].items():
    assert (
        planning._agile_planning_record_version(
            env["project.task"].browse(int(task_id))
        )
        == version
    )
for sprint_id, version in options["expected_versions"]["sprints"].items():
    assert (
        planning._agile_planning_record_version(
            env["project.sprint"].browse(int(sprint_id))
        )
        == version
    )
(output_directory / f"{worker}.ready").write_text("ready\n")
deadline = time.monotonic() + 10
while not (output_directory / "start").exists():
    if time.monotonic() >= deadline:
        raise RuntimeError(f"{worker} did not receive a start signal")
    time.sleep(0.02)

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
    result.update(
        {"outcome": "rejected", "error": str(error), "error_type": type(error).__name__}
    )
except Exception as error:
    env.cr.rollback()
    result.update({"outcome": "failed", "error": f"{type(error).__name__}: {error}"})
(output_directory / f"{worker}.json").write_text(json.dumps(result, sort_keys=True))
if result["outcome"] == "failed":
    raise RuntimeError(result["error"])

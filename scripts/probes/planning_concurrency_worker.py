# Execute one public planning mutation from a separate Odoo process and cursor.

import json
import os
import time
from pathlib import Path

from psycopg2.errors import SerializationFailure

from odoo.exceptions import AccessError, ConcurrencyError, ValidationError


def wait_for(path):
    deadline = time.monotonic() + 10
    while not path.exists():
        assert time.monotonic() < deadline, str(path)
        time.sleep(0.02)


def apply_ownership(env, data, worker):
    uid = (
        data["editor_uid"]
        if worker == "editor" or data["action"] in {"create_sprint", "carryover"}
        else data["member_uid"]
    )
    caller = env["project.task"].with_user(uid).env
    team = caller["project.agile.team"].browse(data["team_id"])
    sprint = caller["project.sprint"].browse(data["sprint_id"])
    if worker == "editor":
        if sprint:
            sprint.write({"team_id": data["other_team_id"]})
        else:
            team.write({"project_id": data["other_project_id"]})
        return
    task = caller["project.task"].browse(data["task_id"])
    values = {"agile_team_id": team.id}
    if sprint:
        values["sprint_id"] = sprint.id
    if data["action"] == "wizard":
        caller["project.sprint.task.assignment.wizard"].create(
            {
                "task_ids": [(6, 0, task.ids)],
                "project_id": data["project_id"],
                "operation": "assign",
                "sprint_id": sprint.id,
            }
        ).action_confirm()
    elif data["action"] == "carryover":
        caller["project.sprint"].browse(
            data["source_sprint_id"]
        )._close_with_disposition("draft_sprint", sprint)
    elif data["action"] == "create_sprint":
        caller["project.sprint"].create(
            {
                "name": "Concurrent new Sprint",
                "project_id": data["project_id"],
                "team_id": team.id,
            }
        )
    elif data["action"].startswith("create_task"):
        caller["project.task"].with_context(
            default_project_id=data["project_id"],
            default_agile_team_id=team.id,
            default_sprint_id=sprint.id,
        ).create(
            {"name": "Concurrent new Task", "agile_item_type_id": data["item_type_id"]}
        )
    else:
        task.write(values)


def ownership_worker(env, directory, worker, data):
    # Both individually valid proposals begin with real, old database snapshots.
    team = env["project.agile.team"].browse(data["team_id"])
    assert team.project_id.id == data["project_id"]
    if data["sprint_id"]:
        sprint = env["project.sprint"].browse(data["sprint_id"])
        assert sprint.team_id == team and sprint.state == "draft"
        assert not sprint.task_ids
    env.cr.execute("SELECT pg_backend_pid()")
    result = {"backend": env.cr.fetchone()[0], "pid": os.getpid(), "retries": 0}
    (directory / f"{worker}.ready").touch()
    wait_for(directory / "start")
    first = data["first"]
    if worker != first:
        wait_for(
            directory / (f"{first}.mutated" if data["contended"] else f"{first}.json")
        )
    for attempt in range(2):
        try:
            env.cr.execute("SET LOCAL lock_timeout = '2s'")
            env.cr.execute("SET LOCAL statement_timeout = '10s'")
            apply_ownership(env, data, worker)
            env.flush_all()
            if worker == first and data["contended"]:
                (directory / f"{worker}.mutated").touch()
                other = "editor" if worker == "member" else "member"
                wait_for(directory / f"{other}.conflict")
            env.cr.commit()
            result["outcome"] = "success"
            break
        except (SerializationFailure, ConcurrencyError) as error:
            env.cr.rollback()
            env.invalidate_all()
            assert attempt == 0, type(error).__name__
            result["retries"] += 1
            result["conflict_type"] = type(error).__name__
            (directory / f"{worker}.conflict").touch()
            wait_for(directory / f"{first}.json")
        except ValidationError as error:
            env.cr.rollback()
            result.update(
                outcome="rejected", error_type=type(error).__name__, error=str(error)
            )
            break
    (directory / f"{worker}.json").write_text(json.dumps(result, sort_keys=True))


output_directory = Path(os.environ["PLANNING_DIRECTORY"])
worker = os.environ["PLANNING_WORKER"]
scenario = json.loads((output_directory / "scenario.json").read_text())
if scenario.get("ownership"):
    ownership_worker(env, output_directory, worker, scenario)
    raise SystemExit(0)
reorder_first, reorder_second, reorder_third = scenario["reorder_task_ids"]
assignment_task_id = (
    scenario["other_assign_task_id"]
    if worker == "assign_other"
    else scenario["assign_task_id"]
)
operations = {
    "assign": (
        "assign",
        [assignment_task_id],
        {
            "sprint_id": scenario["sprint_id"],
            "expected_versions": {
                "tasks": {
                    str(assignment_task_id): scenario["assign_return_versions"][
                        "tasks"
                    ][str(assignment_task_id)]
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
operation, task_ids, options = operations[worker.removesuffix("_other")]
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

if worker == "assign_other":
    wait_for(output_directory / "assign.mutated")
result = {"worker": worker}
try:
    env.cr.execute("SET LOCAL lock_timeout = '2s'")
    env.cr.execute("SET LOCAL statement_timeout = '10s'")
    env["project.project"].apply_agile_planning_change(
        scenario["project_id"], operation, task_ids, **options
    )
    if worker == "assign" and scenario.get("contended_assign"):
        env.flush_all()
        (output_directory / "assign.mutated").touch()
        wait_for(output_directory / "assign_other.json")
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

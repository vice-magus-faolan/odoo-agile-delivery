"""Independent-process planning races in the ordinary installed verifier database."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from odoo.addons.mail.tests.common import mail_new_test_user

assert env.cr.dbname == "odoo_agile_verify_install"
project = env["project.project"].create(
    {
        "name": "Planning concurrency harness",
        "privacy_visibility": "employees",
        "company_id": env.company.id,
        "agile_enabled": True,
        "agile_key": "CONCURRENCY",
    }
)
team = env["project.agile.team"].create(
    {"name": "Planning concurrency team", "project_id": project.id}
)
item_type = env["project.agile.item.type"].create(
    {
        "name": "Planning concurrency story",
        "code": "planning_concurrency_story",
        "can_schedule_in_sprint": True,
    }
)
sprint = env["project.sprint"].create(
    {
        "name": "Planning concurrency Sprint",
        "project_id": project.id,
        "team_id": team.id,
    }
)
return_task = env["project.task"].create(
    {
        "name": "Concurrent return task",
        "project_id": project.id,
        "agile_item_type_id": item_type.id,
    }
)
return_task.assign_product_backlog_to_sprint(sprint)
assign_task = env["project.task"].create(
    {
        "name": "Concurrent assign task",
        "project_id": project.id,
        "agile_item_type_id": item_type.id,
        "agile_backlog_sequence": 40,
    }
)
return_task.write({"agile_backlog_sequence": 50})
reorder_tasks = env["project.task"].create(
    [
        {
            "name": "Concurrent reorder first",
            "project_id": project.id,
            "agile_item_type_id": item_type.id,
            "agile_backlog_sequence": 10,
        },
        {
            "name": "Concurrent reorder second",
            "project_id": project.id,
            "agile_item_type_id": item_type.id,
            "agile_backlog_sequence": 20,
        },
        {
            "name": "Concurrent reorder third",
            "project_id": project.id,
            "agile_item_type_id": item_type.id,
            "agile_backlog_sequence": 30,
        },
    ]
)
planning = env["project.project"]
scenario = {
    "project_id": project.id,
    "sprint_id": sprint.id,
    "return_task_id": return_task.id,
    "assign_task_id": assign_task.id,
    "assign_return_versions": {
        "tasks": {
            str(task.id): planning._agile_planning_record_version(task)
            for task in assign_task | return_task
        },
        "sprints": {str(sprint.id): planning._agile_planning_record_version(sprint)},
    },
    "reorder_task_ids": reorder_tasks.ids,
    "reorder_versions": {
        str(task.id): planning._agile_planning_record_version(task)
        for task in reorder_tasks
    },
}
env.cr.commit()

source = Path("/mnt/probes/planning_concurrency_worker.py").read_text()
command = [
    "odoo",
    "shell",
    "--config=/etc/odoo/odoo.conf",
    "--database",
    env.cr.dbname,
    "--no-http",
]


def launch(directory, worker):
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            **os.environ,
            "PLANNING_WORKER": worker,
            "PLANNING_DIRECTORY": str(directory),
        },
    )
    process.stdin.write(source)
    process.stdin.close()
    process.stdin = None
    return process


def wait_for_ready(directory, workers):
    deadline = time.monotonic() + 10
    while not all((directory / f"{worker}.ready").exists() for worker in workers):
        assert time.monotonic() < deadline, (
            "Planning workers did not reach their pre-mutation rendezvous",
            workers,
        )
        time.sleep(0.05)


def run_scenario(directory, workers, data=None):
    directory.mkdir()
    (directory / "scenario.json").write_text(
        json.dumps(scenario if data is None else data, sort_keys=True)
    )
    processes = []
    results = {}
    try:
        for worker in workers:
            processes.append(launch(directory, worker))
        wait_for_ready(directory, workers)
        (directory / "start").write_text("start\n")
        for worker, process in zip(workers, processes, strict=False):
            stdout, stderr = process.communicate(timeout=20)
            assert process.returncode == 0, (worker, stdout, stderr)
            result_path = directory / f"{worker}.json"
            assert result_path.exists(), (worker, stdout, stderr)
            results[worker] = json.loads(result_path.read_text())
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
    return results


with tempfile.TemporaryDirectory(prefix="planning-concurrency-") as temporary:
    directory = Path(temporary)
    results = run_scenario(directory / "assign-return", ("assign", "return"))
    results.update(
        run_scenario(directory / "reorder", ("reorder_first", "reorder_second"))
    )

# Workers committed in separate cursors; inspect current state, not the seed cache.
env.cr.rollback()
env.invalidate_all()
result_errors = " ".join(result.get("error", "") for result in results.values()).lower()
assert "deadlock" not in result_errors, results
assert "locknotavailable" not in result_errors, results
stale_message = "Sprint Planning changed. Refresh and retry your action."
for pair in (("assign", "return"), ("reorder_first", "reorder_second")):
    outcomes = [results[worker]["outcome"] for worker in pair]
    assert sorted(outcomes) == ["rejected", "success"], (pair, results)
    rejected = next(
        results[worker] for worker in pair if results[worker]["outcome"] == "rejected"
    )
    assert rejected.get("error_type") == "ValidationError", rejected
    assert rejected.get("error") == stale_message, rejected

return_task = env["project.task"].browse(scenario["return_task_id"])
sprint = env["project.sprint"].browse(scenario["sprint_id"])
assign_task = env["project.task"].browse(scenario["assign_task_id"])
assign_won = results["assign"]["outcome"] == "success"
assert assign_task.sprint_id == (sprint if assign_won else env["project.sprint"])
assert return_task.sprint_id == (sprint if assign_won else env["project.sprint"])
assert assign_task.agile_backlog_sequence == 40
assert return_task.agile_backlog_sequence == 50
assert not sprint.scope_event_ids, sprint.scope_event_ids
assert sprint.state == "draft"
assert (
    planning._agile_planning_record_version(sprint)
    == scenario["assign_return_versions"]["sprints"][str(sprint.id)]
)
loser = return_task if assign_won else assign_task
assert (
    planning._agile_planning_record_version(loser)
    == scenario["assign_return_versions"]["tasks"][str(loser.id)]
)
reorder_tasks = (
    env["project.task"]
    .browse(scenario["reorder_task_ids"])
    .sorted(key=lambda task: (task.agile_backlog_sequence, task.id))
)
orders = [task.id for task in reorder_tasks]
first, second, third = scenario["reorder_task_ids"]
assert set(orders) == {first, second, third}, orders
reorder_first_won = results["reorder_first"]["outcome"] == "success"
assert orders == (
    [third, first, second] if reorder_first_won else [second, first, third]
), (orders, results)
sequences = {task.id: task.agile_backlog_sequence for task in reorder_tasks}
assert sequences == {
    first: 10,
    second: 20 if reorder_first_won else 0,
    third: 0 if reorder_first_won else 30,
}, (sequences, results)
for task in reorder_tasks.filtered(
    lambda record: record.id != (third if reorder_first_won else second)
):
    assert (
        planning._agile_planning_record_version(task)
        == scenario["reorder_versions"][str(task.id)]
    )
assert not reorder_tasks.mapped("sprint_id")
assert len(set(orders)) == len(orders)
all_backlog = env["project.task"].search(
    [("project_id", "=", scenario["project_id"]), ("sprint_id", "=", False)],
    order="agile_backlog_sequence, id",
)
all_orders = all_backlog.ids
expected_backlog = orders + ([] if assign_won else [assign_task.id, return_task.id])
assert all_orders == expected_backlog, (all_orders, expected_backlog)
assert len(set(all_orders)) == len(all_orders)


def ownership_scenario(action, key, first="member", contended=False):
    projects = env["project.project"].create(
        [
            {
                "name": "Ownership race " + key + suffix,
                "privacy_visibility": "employees",
                "company_id": env.company.id,
                "agile_enabled": True,
                "agile_key": key + suffix,
            }
            for suffix in ("A", "B")
        ]
    )
    teams = env["project.agile.team"].create(
        [{"name": name, "project_id": projects[0].id} for name in ("Dev", "BA")]
    )
    target = env["project.sprint"]
    if action in {"task_sprint", "create_task_sprint", "wizard", "carryover"}:
        target = env["project.sprint"].create(
            {
                "name": "Empty Draft",
                "project_id": projects[0].id,
                "team_id": teams[0].id,
            }
        )
    task = env["project.task"].create(
        {
            "name": "Ownership race work",
            "project_id": projects[0].id,
            "agile_item_type_id": item_type.id,
        }
    )
    source_sprint = env["project.sprint"]
    if action == "carryover":
        source_sprint = target.copy({"name": "Carry-over source"})
        task.write({"sprint_id": source_sprint.id})
        source_sprint.action_start()
    data = {
        "ownership": True,
        "action": action,
        "first": first,
        "contended": contended,
        "project_id": projects[0].id,
        "other_project_id": projects[1].id,
        "team_id": teams[0].id,
        "other_team_id": teams[1].id,
        "sprint_id": target.id,
        "source_sprint_id": source_sprint.id,
        "task_id": task.id,
        "item_type_id": item_type.id,
        "member_uid": member_user.id,
        "editor_uid": editor_user.id,
    }
    env.cr.commit()
    return data


def check_ownership_race(directory, data):
    results = run_scenario(directory, ("member", "editor"), data)
    print(  # pylint: disable=print-used
        "OWNERSHIP_RACE_RESULT "
        + json.dumps(
            {"action": data["action"], "first": data["first"], "workers": results},
            sort_keys=True,
        ),
        flush=True,
    )
    assert sorted(row["outcome"] for row in results.values()) == [
        "rejected",
        "success",
    ], results
    first = data["first"]
    second = "editor" if first == "member" else "member"
    assert results[first]["outcome"] == "success", results
    assert results[first]["retries"] == 0, results
    assert results[second]["outcome"] == "rejected", results
    assert results[second]["retries"] == 1, results
    assert results[second]["error_type"] == "ValidationError", results
    assert results[second]["conflict_type"] == (
        "ConcurrencyError" if data["contended"] else "SerializationFailure"
    ), results
    if second == "editor":
        expected_error = (
            "Assigned tasks must keep their Project and Sprint team."
            if data["sprint_id"]
            else "A team used by tasks or Sprints cannot change Project."
        )
    else:
        expected_error = {
            "task_sprint": "The task team must match the Sprint team.",
            "create_task_sprint": "The task team must match the Sprint team.",
            "task_team": "The task team must belong to its Agile Project and company.",
            "create_task_team": (
                "The task team must belong to its Agile Project and company."
            ),
            "create_sprint": "The Agile team must belong to the Sprint project.",
            "carryover": (
                "Carry-over requires a different draft Sprint "
                "for the same project, company, and Agile team."
            ),
        }[data["action"]]
    assert results[second]["error"] == expected_error, results
    assert results["member"]["backend"] != results["editor"]["backend"], results
    assert results["member"]["pid"] != results["editor"]["pid"], results
    env.cr.rollback()
    env.invalidate_all()
    team = env["project.agile.team"].browse(data["team_id"])
    sprint = env["project.sprint"].browse(data["sprint_id"])
    tasks = env["project.task"].search([("project_id", "=", data["project_id"])])
    assert all(
        task.agile_team_id.project_id == task.project_id
        for task in tasks
        if task.agile_team_id
    )
    assert all(
        task.agile_team_id == task.sprint_id.team_id for task in tasks if task.sprint_id
    )
    assert len(tasks) == 1 + (
        data["action"].startswith("create_task") and first == "member"
    )
    sprints = env["project.sprint"].search([("project_id", "=", data["project_id"])])
    assert all(row.team_id.project_id == row.project_id for row in sprints)
    if data["action"] == "create_sprint":
        assert len(sprints) == (1 if first == "member" else 0)
    if data["action"] == "carryover":
        source = env["project.sprint"].browse(data["source_sprint_id"])
        task = env["project.task"].browse(data["task_id"])
        assert source.state == ("closed" if first == "member" else "active")
        assert task.sprint_id == (sprint if first == "member" else source)
        assert source.scope_event_ids.mapped("event_type") == (
            ["committed", "carried_to_sprint"] if first == "member" else ["committed"]
        )
    if sprint:
        assert sprint.team_id.id == (
            data["team_id"] if first == "member" else data["other_team_id"]
        )
    else:
        assert team.project_id.id == (
            data["project_id"] if first == "member" else data["other_project_id"]
        )
    print(  # pylint: disable=print-used
        "OWNERSHIP_RACE_OK "
        + json.dumps(
            {"action": data["action"], "first": first, "workers": results},
            sort_keys=True,
        ),
        flush=True,
    )


member_user = mail_new_test_user(
    env, "ownership_member", groups="project.group_project_user"
)
editor_user = mail_new_test_user(
    env, "ownership_editor", groups="project.group_project_manager"
)
with tempfile.TemporaryDirectory(
    prefix="planning-ownership-", dir="/var/lib/odoo"
) as temporary:
    failures = []
    cases = [
        (action, first, False)
        for action in (
            "task_sprint",
            "task_team",
            "create_task_sprint",
            "create_task_team",
            "create_sprint",
            "wizard",
            "carryover",
        )
        for first in ("member", "editor")
        if action != "wizard" or first == "member"
    ] + [
        (action, first, True)
        for action in ("task_sprint", "task_team")
        for first in ("member", "editor")
    ]
    for index, (action, first, contended) in enumerate(cases):
        data = ownership_scenario(action, "OWNRACE" + str(index), first, contended)
        try:
            check_ownership_race(Path(temporary) / str(index), data)
        except AssertionError as error:
            failures.append((action, str(error)))
    assert not failures, failures

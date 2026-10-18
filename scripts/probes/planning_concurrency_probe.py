"""Independent-process planning races in the ordinary installed verifier database."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

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


def run_scenario(directory, workers):
    directory.mkdir()
    (directory / "scenario.json").write_text(json.dumps(scenario, sort_keys=True))
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

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
conflict_task = env["project.task"].create(
    {
        "name": "Concurrent assign-return task",
        "project_id": project.id,
        "agile_item_type_id": item_type.id,
    }
)
conflict_task.assign_product_backlog_to_sprint(sprint)
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
    "conflict_task_id": conflict_task.id,
    "assign_return_versions": {
        "tasks": {
            str(conflict_task.id): planning._agile_planning_record_version(
                conflict_task
            )
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
assert results["return"]["outcome"] == "success", results
assert results["assign"]["outcome"] == "rejected", results
assert all(
    result["outcome"] in {"success", "rejected"} for result in results.values()
), results
assert any(
    result["outcome"] == "success"
    for result in (results["reorder_first"], results["reorder_second"])
), results

conflict_task = env["project.task"].browse(scenario["conflict_task_id"])
sprint = env["project.sprint"].browse(scenario["sprint_id"])
assert not conflict_task.sprint_id, conflict_task.sprint_id
assert not sprint.scope_event_ids, sprint.scope_event_ids
reorder_tasks = (
    env["project.task"]
    .browse(scenario["reorder_task_ids"])
    .sorted(key=lambda task: (task.agile_backlog_sequence, task.id))
)
orders = [task.id for task in reorder_tasks]
first, second, third = scenario["reorder_task_ids"]
assert set(orders) == {first, second, third}, orders
assert orders.index(first) > min(orders.index(second), orders.index(third)), orders
assert not reorder_tasks.mapped("sprint_id")
assert len(set(orders)) == len(orders)
all_backlog = env["project.task"].search(
    [("project_id", "=", scenario["project_id"]), ("sprint_id", "=", False)],
    order="agile_backlog_sequence, id",
)
all_orders = all_backlog.ids
assert set(all_orders) == {scenario["conflict_task_id"], first, second, third}, (
    all_orders
)
assert len(set(all_orders)) == len(all_orders)
assertion = {
    "database": env.cr.dbname,
    "all_orders": all_orders,
    "orders": orders,
    "results": results,
}
# Stdout exposes both race outcomes alongside the ordinary verifier result.
print(  # pylint: disable=print-used
    "PLANNING_CONCURRENCY=" + json.dumps(assertion, sort_keys=True), flush=True
)

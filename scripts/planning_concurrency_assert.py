# Assert serialized outcomes and no partial state after external planning races.

import json
from pathlib import Path


output_directory = Path("/mnt/planning-concurrency")
scenario = json.loads((output_directory / "scenario.json").read_text())
results = {
    name: json.loads((output_directory / f"{name}.json").read_text())
    for name in ("assign", "return", "reorder_first", "reorder_second")
}
result_errors = " ".join(result.get("error", "") for result in results.values()).lower()
assert "deadlock" not in result_errors, results
assert "locknotavailable" not in result_errors, results
assert results["return"]["outcome"] == "success", results
assert results["assign"]["outcome"] == "rejected", results
assert sum(result["outcome"] == "success" for result in (results["reorder_first"], results["reorder_second"])) == 1, results
assert sum(result["outcome"] == "rejected" for result in (results["reorder_first"], results["reorder_second"])) == 1, results

conflict_task = env["project.task"].browse(scenario["conflict_task_id"])
sprint = env["project.sprint"].browse(scenario["sprint_id"])
assert not conflict_task.sprint_id, conflict_task.sprint_id
assert not sprint.scope_event_ids, sprint.scope_event_ids
reorder_tasks = env["project.task"].browse(scenario["reorder_task_ids"]).sorted(
    key=lambda task: (task.agile_backlog_sequence, task.id)
)
orders = [task.id for task in reorder_tasks]
first, second, third = scenario["reorder_task_ids"]
assert orders in ([third, first, second], [second, first, third]), orders
assert [task.agile_backlog_sequence for task in reorder_tasks] == [20, 30, 40]
assert not reorder_tasks.mapped("sprint_id")
assert len(set(orders)) == len(orders)
all_backlog = env["project.task"].search(
    [("project_id", "=", scenario["project_id"]), ("sprint_id", "=", False)],
    order="agile_backlog_sequence, id",
)
all_orders = all_backlog.ids
assert all_orders in (
    [scenario["conflict_task_id"], third, first, second],
    [scenario["conflict_task_id"], second, first, third],
), all_orders
assert all_backlog.mapped("agile_backlog_sequence") == [10, 20, 30, 40]
assertion = {
    "database": "odoo_agile_planning_concurrency_t_b1f7013f",
    "all_orders": all_orders,
    "orders": orders,
    "results": results,
}
(output_directory / "assertion.json").write_text(json.dumps(assertion, sort_keys=True))

# Create fresh fixture records for the external planning-concurrency harness.

import json
from pathlib import Path

output_directory = Path("/mnt/planning-concurrency")
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
(output_directory / "scenario.json").write_text(json.dumps(scenario, sort_keys=True))

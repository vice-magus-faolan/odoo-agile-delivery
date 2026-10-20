"""Upgrade pointed Stories in an active Sprint and check points and events."""

import json
import logging

from odoo import Command

PHASE = globals()["PHASE"]
env = globals()["env"]

TASK_FIELDS = [
    "name",
    "agile_story_points",
    "agile_key",
    "agile_item_type_id",
    "sprint_id",
]
EVENT_FIELDS = [
    "sprint_id",
    "task_id",
    "event_type",
    "story_points",
    "previous_story_points",
    "actor_id",
    "event_at",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
]
SNAPSHOT_KEY = "project_agile.item_type_upgrade_snapshot"


def snapshot(records, field_names):
    return json.loads(json.dumps(records.read(field_names), default=str))


if PHASE == "seed":
    task_type = env.ref("project_agile.project_agile_item_type_task")
    task_type.write({"name": "Customer task", "sequence": 123})
    project = env["project.project"].create(
        {
            "name": "Item policy upgrade client",
            "agile_enabled": True,
            "agile_key": "UPGRADETYPE",
            "agile_estimation_method": "fibonacci",
            "agile_default_item_type_id": False,
        }
    )
    untyped = env["project.task"].create(
        {
            "name": "Existing untyped work",
            "project_id": project.id,
            "agile_item_type_id": False,
        }
    )
    story = env.ref("project_agile.project_agile_item_type_story")
    tasks = env["project.task"].create(
        [
            {
                "name": f"Existing Story {points}",
                "project_id": project.id,
                "agile_item_type_id": story.id,
                "agile_story_points": points,
            }
            for points in (3, 5, 8)
        ]
    )
    team = env["project.agile.team"].create(
        {"name": "Upgrade team", "project_id": project.id}
    )
    sprint = env["project.sprint"].create(
        {
            "name": "Existing active Sprint",
            "project_id": project.id,
            "team_id": team.id,
            "task_ids": [Command.set(tasks.ids)],
        }
    )
    sprint.action_start()
    env.flush_all()
    env["ir.config_parameter"].set_param(
        SNAPSHOT_KEY,
        json.dumps(
            {
                "project": project.id,
                "sprint": sprint.id,
                "untyped": untyped.id,
                "tasks": snapshot(tasks, TASK_FIELDS),
                "events": snapshot(sprint.scope_event_ids, EVENT_FIELDS),
            }
        ),
    )
    env.cr.commit()
    logging.getLogger(__name__).info(
        "Seeded an active Sprint with Stories at 3/5/8 points."
    )
elif PHASE == "check":
    saved = json.loads(env["ir.config_parameter"].get_param(SNAPSHOT_KEY))
    project = env["project.project"].browse(saved["project"])
    sprint = env["project.sprint"].browse(saved["sprint"])
    tasks = env["project.task"].browse(row["id"] for row in saved["tasks"])
    # Read before editing a task so writes cannot hide a missing points backfill.
    assert tasks.mapped("agile_effective_story_points") == [3, 5, 8]
    assert all(tasks.mapped("agile_uses_story_points"))
    assert snapshot(tasks, TASK_FIELDS) == saved["tasks"], (
        "task preservation",
        saved["tasks"],
        snapshot(tasks, TASK_FIELDS),
    )
    assert snapshot(sprint.scope_event_ids, EVENT_FIELDS) == saved["events"], (
        "event preservation",
        saved["events"],
        snapshot(sprint.scope_event_ids, EVENT_FIELDS),
    )
    assert sprint.state == "active" and sprint.committed_task_ids == tasks
    assert not project.agile_default_item_type_id
    assert not env["project.task"].browse(saved["untyped"]).agile_item_type_id
    task_type = env.ref("project_agile.project_agile_item_type_task")
    assert task_type.name == "Customer task" and task_type.sequence == 123
    for code in ("configuration", "data_import"):
        item_type = env.ref("project_agile.project_agile_item_type_" + code)
        assert item_type.active and not item_type.uses_story_points
        assert item_type.can_schedule_in_sprint

    def ui_points(expected):
        planning = env["project.project"].get_agile_planning_snapshot(project.id)
        row = next(row for row in planning["sprints"] if row["id"] == sprint.id)
        assert row["current_points"] == expected
        assert row["committed_points"] == 16
        assert sum(item["story_points"] for item in row["items"]) == expected

    ui_points(16)
    tasks[0].write({"agile_story_points": 5})
    event = sprint.scope_event_ids.sorted("id")[-1]
    assert event.event_type == "reestimated" and event.task_id == tasks[0]
    assert (event.previous_story_points, event.story_points) == (3, 5)
    ui_points(18)
    tasks[1].write(
        {
            "agile_item_type_id": env.ref(
                "project_agile.project_agile_item_type_configuration"
            ).id,
        }
    )
    event = sprint.scope_event_ids.sorted("id")[-1]
    assert event.event_type == "reestimated" and event.task_id == tasks[1]
    assert (event.previous_story_points, event.story_points) == (5, 0)
    assert tasks[1].agile_story_points == 5
    ui_points(13)
    assert len(sprint.scope_event_ids) == len(saved["events"]) + 2
    new_project = env["project.project"].create(
        {"name": "New after update", "agile_enabled": True, "agile_key": "AFTERTYPE"}
    )
    assert new_project.agile_default_item_type_id == task_type
    quick = (
        env["project.task"]
        .with_context(default_project_id=new_project.id)
        .create({"name": "Quick after update"})
    )
    assert quick.agile_item_type_id == task_type
    logging.getLogger(__name__).info(
        "Upgrade passed: Story points and Sprint events preserved; "
        "point changes, planning totals, seeds and quick defaults checked."
    )
else:
    raise AssertionError("Unknown item-type lifecycle phase")

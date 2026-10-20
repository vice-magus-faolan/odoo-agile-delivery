"""Populated item-type update, run by scripts/verify on its owned database."""

import logging

PHASE = globals()["PHASE"]
env = globals()["env"]

# PHASE and env are supplied by the existing native Odoo shell caller.
if PHASE == "seed":
    task_type = env.ref("project_agile.project_agile_item_type_task")
    task_type.write({"name": "Customer task", "sequence": 123})
    project = env["project.project"].create(
        {
            "name": "Item policy upgrade client",
            "agile_enabled": True,
            "agile_key": "UPGRADETYPE",
            "agile_default_item_type_id": False,
        }
    )
    env["project.task"].create(
        {
            "name": "Existing untyped work",
            "project_id": project.id,
            "agile_item_type_id": False,
        }
    )
    # Model missing new seeds in a populated installation without resetting data.
    for code in ("configuration", "data_import"):
        item_type = env.ref("project_agile.project_agile_item_type_" + code)
        env["ir.model.data"].search(
            [
                ("module", "=", "project_agile"),
                ("name", "=", "project_agile_item_type_" + code),
            ]
        ).unlink()
        item_type.unlink()
    # Simulate the populated pre-release state: the Scrum column already exists,
    # but the BA seeds and this release migration have not been applied.
    env["ir.module.module"].search([("name", "=", "project_scrum")]).write(
        {"latest_version": "19.0.1.1.0"}
    )
    env.cr.commit()
elif PHASE == "check":
    task_type = env.ref("project_agile.project_agile_item_type_task")
    assert task_type.name == "Customer task" and task_type.sequence == 123
    project = env["project.project"].search([("agile_key", "=", "UPGRADETYPE")])
    assert len(project) == 1 and not project.agile_default_item_type_id
    existing = env["project.task"].search([("project_id", "=", project.id)])
    assert len(existing) == 1 and not existing.agile_item_type_id
    for code in ("configuration", "data_import"):
        item_type = env.ref("project_agile.project_agile_item_type_" + code)
        assert item_type.active and not item_type.uses_story_points
        assert item_type.can_schedule_in_sprint
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
        "Populated item-type update preserves client work and customizations; "
        "BA seeds and new quick defaults passed."
    )
else:
    raise AssertionError("Unknown item-type lifecycle phase")

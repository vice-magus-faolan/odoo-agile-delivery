"""Disposable optional-bridge proof and independent relink/Sprint event races."""

import json

from odoo.addons.project_agile_solution.tests.task_concurrency import race, seed

assert env.cr.dbname == "odoo_agile_verify_install"
for name in ("project_agile_solution", "project_scrum", "project_agile_solution_scrum"):
    assert env["ir.module.module"].search([("name", "=", name)]).state == "installed"
for name in ("project_agile_git", "project_scrum_analytics", "sale", "document_page"):
    module = env["ir.module.module"].search([("name", "=", name)])
    assert not module or module.state != "installed", name
# Canonical discovery and race receipts are intentionally written to stdout.
print("M8_ISOLATED_SOLUTION_SCRUM_INSTALL_OK", flush=True)  # pylint: disable=print-used
results = []
for index, (winner_action, loser_action, ordering) in enumerate(
    (
        ("relink", "start", "committed"),
        ("start", "relink", "committed"),
        ("start", "relink", "contended"),
        ("relink", "add", "committed"),
        ("relink", "close", "committed"),
    )
):
    manager, project, solution, revision = seed(env, "M8SCOPERACE" + str(index))
    task = (
        env["project.task"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC scope race",
                "project_id": project.id,
                "agile_item_type_id": env.ref(
                    "project_agile.project_agile_item_type_story"
                ).id,
            }
        )
    )
    link = (
        env["project.agile.requirement.task.link"]
        .with_user(manager)
        .create({"task_id": task.id, "requirement_revision_id": revision.id})
    )
    successor = revision.browse(revision.requirement_id.action_new_revision()["res_id"])
    successor.write({"description": "SYNTHETIC deliberately changed v2"})
    team = (
        env["project.agile.team"]
        .with_user(manager)
        .create({"name": "SYNTHETIC race team", "project_id": project.id})
    )
    sprint = (
        env["project.sprint"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC race sprint",
                "project_id": project.id,
                "team_id": team.id,
            }
        )
    )
    if loser_action == "add":
        sprint.action_start()
    else:
        task.write({"sprint_id": sprint.id})
    if loser_action == "close":
        sprint.action_start()
    expected = revision if winner_action == "start" else successor
    frozen_payload = json.loads(
        json.dumps(
            {"requirement": expected._snapshot_values(), "specification": None},
            sort_keys=True,
            default=str,
        )
    )
    env.cr.commit()
    common = {
        "uid": manager.id,
        "task_id": task.id,
        "sprint_id": sprint.id,
        "successor_id": successor.id,
    }
    workers = race(
        env,
        {**common, "action": winner_action},
        {**common, "action": loser_action},
        ordering=ordering,
    )
    event_type = {"start": "committed", "add": "added", "close": "carried_to_backlog"}[
        loser_action if loser_action != "relink" else winner_action
    ]
    event = (
        env["project.sprint.scope.event"]
        .with_user(manager)
        .search([("task_id", "=", task.id), ("event_type", "=", event_type)])
    )
    contexts = (
        env["project.agile.solution.sprint.context"]
        .with_user(manager)
        .search([("scope_event_id", "=", event.id)])
    )
    assert len(event) == 1 and event.solution_capture_status == "captured"
    assert len(contexts) == 1
    assert contexts.requirement_revision_id == expected, (
        winner_action,
        loser_action,
        contexts.requirement_revision_id.ids,
    )
    assert json.loads(contexts.payload_json) == frozen_payload
    assert not link.active
    current_links = link.search([("task_id", "=", task.id)])
    assert len(current_links) == 1
    assert current_links.requirement_revision_id == successor
    assert (
        link.with_context(active_test=False).search_count([("task_id", "=", task.id)])
        == 2
    )
    results.append(
        {
            "winner": winner_action,
            "loser": loser_action,
            "captured_revision": expected.number,
            "ordering": ordering,
            "workers": workers,
        }
    )
print(  # pylint: disable=print-used
    "M8_SCRUM_TRACE_CONCURRENCY_OK " + json.dumps({"races": results}, sort_keys=True),
    flush=True,
)

# Extend the existing production-action race fixture for close selection/claims.
close_results = []
for index, (winner_action, loser_action) in enumerate(
    (
        ("complete", "close"),
        ("remove", "close"),
        ("close", "complete"),
        ("close", "create_in_sprint"),
        ("change_target", "close"),
    )
):
    manager, project, solution, revision = seed(env, "SCRUMCLOSE" + str(index))
    team = (
        env["project.agile.team"]
        .with_user(manager)
        .create({"name": "SYNTHETIC close team", "project_id": project.id})
    )
    sprint = (
        env["project.sprint"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC close source",
                "project_id": project.id,
                "team_id": team.id,
            }
        )
    )
    task = (
        env["project.task"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC close work",
                "project_id": project.id,
                "agile_item_type_id": env.ref(
                    "project_agile.project_agile_item_type_story"
                ).id,
                "sprint_id": sprint.id,
            }
        )
    )
    sprint.action_start()
    common = {"uid": manager.id, "task_id": task.id, "sprint_id": sprint.id}
    target = env["project.sprint"]
    if winner_action == "change_target":
        target = (
            env["project.sprint"]
            .with_user(manager)
            .create(
                {
                    "name": "SYNTHETIC close target",
                    "project_id": project.id,
                    "team_id": team.id,
                }
            )
        )
        other_team = (
            env["project.agile.team"]
            .with_user(manager)
            .create({"name": "SYNTHETIC changed target team", "project_id": project.id})
        )
        common.update({"target_id": target.id, "other_team_id": other_team.id})
    count = env["project.task"].search_count([("project_id", "=", project.id)])
    committed = sprint.committed_task_ids.ids
    env.cr.commit()
    rejected = loser_action == "create_in_sprint" or winner_action == "change_target"
    workers = race(
        env,
        {**common, "action": winner_action},
        {**common, "action": loser_action, "expect_stale": rejected},
    )
    assert sprint.committed_task_ids.ids == committed
    assert env["project.task"].search_count([("project_id", "=", project.id)]) == count
    events = sprint.scope_event_ids
    assert "carried_to_sprint" not in events.mapped("event_type")
    if winner_action == "change_target":
        assert sprint.state == "active" and not sprint.closed_at
        assert task.sprint_id == sprint and not target.task_ids
        assert events.mapped("event_type") == ["committed"]
    else:
        assert sprint.state == "closed" and sprint.closed_at
        if winner_action == "complete":
            assert task.sprint_id == sprint and task.state == "1_done"
            assert events.mapped("event_type") == ["committed", "completed"]
        elif winner_action == "remove":
            assert not task.sprint_id
            assert events.mapped("event_type") == ["committed", "removed"]
        else:
            assert not task.sprint_id
            assert events.mapped("event_type") == ["committed", "carried_to_backlog"]
    close_results.append(
        {"winner": winner_action, "loser": loser_action, "workers": workers}
    )
print(  # pylint: disable=print-used
    "SCRUM_CLOSE_CONCURRENCY_OK "
    + json.dumps({"races": close_results}, sort_keys=True),
    flush=True,
)

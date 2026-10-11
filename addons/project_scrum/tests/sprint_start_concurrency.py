"""Real independent start transactions on an owned, initialized disposable DB.

Run from Odoo shell after server installation, not a TransactionCase cursor.
Only this fixture commits; production lifecycle code never owns transactions.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier

from psycopg2 import IntegrityError

from odoo import Command, api
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import ValidationError


def _start(registry, uid, sprint_id, rendezvous):
    with registry.cursor() as cr:
        env = api.Environment(cr, uid, {})
        cr.execute("SET LOCAL statement_timeout = '30s'")
        cr.execute("SELECT pg_backend_pid()")
        backend = cr.fetchone()[0]
        sprint = env["project.sprint"].browse(sprint_id)
        assert sprint.state == "draft"  # Establish independent snapshots.
        rendezvous.wait(timeout=15)
        try:
            sprint.action_start()
        except ValidationError as error:
            assert "Only one Sprint can be active" in str(error), str(error)
            assert isinstance(error.__cause__, IntegrityError), repr(error.__cause__)
            assert error.__cause__.diag.constraint_name == "project_sprint_active_project_team_unique"
            assert sprint.state == "draft"
            assert not sprint.committed_task_ids and not sprint.scope_event_ids
            result = {"sprint_id": sprint_id, "backend": backend,
                      "outcome": "rejected", "error": str(error)}
        else:
            assert sprint.state == "active"
            assert sprint.committed_task_ids == sprint.task_ids
            assert sorted(sprint.scope_event_ids.mapped("event_type")) == ["committed", "completed"]
            result = {"sprint_id": sprint_id, "backend": backend, "outcome": "started"}
        # Commit even the rejected transaction: the lifecycle savepoint must
        # already have removed every partial commitment/event and healed cr.
        cr.commit()
        return result


def run_probe(env):
    assert env.cr.dbname == "odoo_agile_scrum_uniqueness", env.cr.dbname
    manager = mail_new_test_user(env, "scrum_start_race_manager",
                                groups="project.group_project_manager")
    results = []
    for iteration in range(3):
        project = env["project.project"].create({
            "name": "Synthetic concurrent Sprint starts", "agile_enabled": True,
            "agile_key": "STARTRACE" + str(iteration), "privacy_visibility": "employees",
            "company_id": env.company.id,
        })
        team = env["project.agile.team"].create({"name": "Race team", "project_id": project.id})
        sprints = env["project.sprint"].create([
            {"name": "Race " + name, "project_id": project.id, "team_id": team.id}
            for name in ("A", "B")
        ])
        for sprint in sprints:
            env["project.task"].create({
                "name": "Completed commitment " + sprint.name, "project_id": project.id,
                "agile_item_type_id": env.ref("project_agile.project_agile_item_type_story").id,
                "sprint_id": sprint.id, "state": "1_done",
            })
        env.cr.commit()
        rendezvous = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(_start, env.registry, manager.id, sprint.id, rendezvous)
                       for sprint in sprints]
            workers = [future.result(timeout=60) for future in futures]
        assert len({row["backend"] for row in workers}) == 2, workers
        assert sorted(row["outcome"] for row in workers) == ["rejected", "started"], workers
        env.cr.rollback()
        env.invalidate_all()
        active = sprints.filtered(lambda sprint: sprint.state == "active")
        draft = sprints - active
        assert len(active) == len(draft) == 1
        assert active.committed_task_ids == active.task_ids
        assert sorted(active.scope_event_ids.mapped("event_type")) == ["committed", "completed"]
        assert not draft.committed_task_ids and not draft.scope_event_ids
        assert len(draft.task_ids) == 1 and draft.task_ids.state == "1_done"
        results.append({"iteration": iteration, "workers": workers,
                        "active": active.id, "draft": draft.id})
    print("SPRINT_START_CONCURRENCY_OK " + json.dumps(results, sort_keys=True), flush=True)

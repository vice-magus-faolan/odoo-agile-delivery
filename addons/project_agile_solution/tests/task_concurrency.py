"""Independent Odoo transactions prove intent reuse and Task/event serialization.

Only imported disposable fixture code commits/rolls back or launches processes.
No customer database or runtime service is selected by caller values.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from psycopg2.errors import SerializationFailure

from odoo.exceptions import ConcurrencyError, ValidationError

from .baseline_concurrency import _wait


def worker(env):
    data = json.loads(os.environ["SOLUTION_TASK_RACE"])
    assert env.cr.dbname == "odoo_agile_verify_install"
    directory, name = Path(data["directory"]), data["worker"]
    uid = data["uid"]
    intent = (
        env["project.agile.solution.task.intent"]
        .with_user(uid)
        .browse(data.get("intent_id", []))
    )
    task = env["project.task"].with_user(uid).browse(data.get("task_id", []))
    (intent or task).read(["name"])  # Force a stale repeatable-read snapshot.
    env.cr.execute("SELECT pg_backend_pid()")
    backend = env.cr.fetchone()[0]
    (directory / (name + ".ready")).touch()
    _wait(directory / (name + ".go"))
    retries = 0
    while retries < 4:
        (directory / (name + ".attempt")).touch()
        try:
            try:
                result_id = _apply(env, data)
            except ValidationError:
                if not data.get("expect_stale"):
                    raise
                env.cr.rollback()
                result_id = 0
            if name == "winner":
                (directory / "winner.mutated").touch()
                _wait(directory / "winner.commit")
            env.cr.commit()
            (directory / (name + ".json")).write_text(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "backend": backend,
                        "retries": retries,
                        "result_id": result_id,
                    }
                )
            )
            return
        except (SerializationFailure, ConcurrencyError):
            env.cr.rollback()
            env.invalidate_all()
            retries += 1
            time.sleep(0.1)
    raise AssertionError("Task trace race exhausted bounded retry")


def _apply(env, data):
    uid, action = data["uid"], data["action"]
    if action == "edit_requirement":
        intent = (
            env["project.agile.solution.task.intent"]
            .with_user(uid)
            .browse(data["intent_id"])
        )
        intent.requirement_revision_ids.write(
            {"rationale": "SYNTHETIC concurrent source change"}
        )
        return intent.id
    if action == "confirm":
        return (
            env["project.agile.solution.task.intent"]
            .with_user(uid)
            .browse(data["intent_id"])
            .action_confirm()["res_id"]
        )
    task = env["project.task"].with_user(uid).browse(data["task_id"])
    sprint = env["project.sprint"].with_user(uid).browse(data["sprint_id"])
    if action == "relink":
        links = (
            env["project.agile.requirement.task.link"]
            .with_user(uid)
            .search([("task_id", "=", task.id)])
        )
        links.action_retire("SYNTHETIC independent deliberate successor")
        env["project.agile.requirement.task.link"].with_user(uid).create(
            {"task_id": task.id, "requirement_revision_id": data["successor_id"]}
        )
    elif action == "start":
        sprint.action_start()
    elif action == "add":
        task.write({"sprint_id": sprint.id})
    elif action == "close":
        target = env["project.sprint"].with_user(uid).browse(data.get("target_id", []))
        sprint._close_with_disposition(
            "draft_sprint" if target else "product_backlog", target
        )
    elif action == "complete":
        task.write({"state": "1_done"})
    elif action == "remove":
        task.return_sprint_tasks_to_product_backlog()
    elif action == "create_in_sprint":
        task.copy({"name": "SYNTHETIC concurrent new work", "sprint_id": sprint.id})
    elif action == "change_target":
        env["project.sprint"].with_user(uid).browse(data["target_id"]).write(
            {"team_id": data["other_team_id"]}
        )
        # Hold the changed target row before releasing the loser.
        env.flush_all()
    else:
        raise AssertionError("Unknown fixture action")
    return task.id


def race(env, winner, loser):
    assert env.cr.dbname == "odoo_agile_verify_install"
    with tempfile.TemporaryDirectory(
        prefix="solution-task-race-", dir="/var/lib/odoo"
    ) as temporary:
        directory, processes = Path(temporary), []
        try:
            for name, proposal in (("winner", winner), ("loser", loser)):
                data = {**proposal, "directory": str(directory), "worker": name}
                process = subprocess.Popen(
                    [
                        "odoo",
                        "shell",
                        "--config=/etc/odoo/odoo.conf",
                        "--database",
                        env.cr.dbname,
                        "--no-http",
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={**os.environ, "SOLUTION_TASK_RACE": json.dumps(data)},
                )
                processes.append(process)
                assert process.stdin is not None
                process.stdin.write(
                    "from odoo.addons.project_agile_solution.tests.task_concurrency "
                    "import worker\nworker(env)\n"
                )
                process.stdin.close()
                process.stdin = None
            for name in ("winner", "loser"):
                _wait(directory / (name + ".ready"))
            (directory / "winner.go").touch()
            _wait(directory / "winner.mutated")
            (directory / "loser.go").touch()
            _wait(directory / "loser.attempt")
            (directory / "winner.commit").touch()
            for process in processes:
                stdout, stderr = process.communicate(timeout=60)
                assert process.returncode == 0, (stdout, stderr)
            results = [
                json.loads((directory / (name + ".json")).read_text())
                for name in ("winner", "loser")
            ]
            assert (
                results[0]["pid"] != results[1]["pid"]
                and results[0]["backend"] != results[1]["backend"]
            )
            # Capture-first relinking need not read or rewrite the captured event.
            # Its exact historical content is asserted by the bridge consumer.
            if (winner["action"], loser["action"]) == ("start", "relink"):
                assert results[1]["retries"] == 0, results
            else:
                assert results[1]["retries"] >= 1, results
            if loser.get("expect_stale"):
                assert results[1]["result_id"] == 0, results
            else:
                assert results[0]["result_id"] == results[1]["result_id"], results
            env.cr.rollback()
            env.invalidate_all()
            return results
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)


def seed(env, key):
    from odoo import Command

    from odoo.addons.mail.tests.common import mail_new_test_user

    manager = mail_new_test_user(
        env,
        key.lower() + "_manager",
        groups="project.group_project_manager",
        company_id=env.company.id,
        company_ids=[Command.set(env.company.ids)],
    )
    project = env["project.project"].create(
        {
            "name": "SYNTHETIC " + key,
            "agile_enabled": True,
            "agile_key": key,
            "company_id": env.company.id,
            "privacy_visibility": "employees",
        }
    )
    solution = (
        env["project.agile.solution"]
        .with_user(manager)
        .create({"name": "SYNTHETIC trace race", "project_id": project.id})
    )
    identity = (
        env["project.agile.requirement"]
        .with_user(manager)
        .create({"name": "SYNTHETIC requirement", "solution_id": solution.id})
    )
    revision = (
        env["project.agile.requirement.revision"]
        .with_user(manager)
        .create(
            {
                "requirement_id": identity.id,
                "title": "SYNTHETIC intent",
                "description": "A bounded synthetic outcome",
                "rationale": "Traceability",
                "verification_method": "Independent native transactions",
                "acceptance_expectations": "No duplicate or rewritten commitment",
            }
        )
    )
    return manager, project, solution, revision


def run_probe(env):
    from odoo import Command

    assert env.cr.dbname == "odoo_agile_verify_install"
    manager, project, solution, revision = seed(env, "M8TASKRACE")
    results = []
    for operation in ("create", "link"):
        values = {
            "solution_id": solution.id,
            "name": "SYNTHETIC deliberate race " + operation,
            "operation": operation,
            "agile_item_type_id": env.ref(
                "project_agile.project_agile_item_type_story"
            ).id,
            "requirement_revision_ids": [Command.set(revision.ids)],
        }
        if operation == "link":
            task = (
                env["project.task"]
                .with_user(manager)
                .create(
                    {
                        "name": "SYNTHETIC existing race work",
                        "project_id": project.id,
                        "agile_item_type_id": values["agile_item_type_id"],
                    }
                )
            )
            values["task_id"] = task.id
        intent = (
            env["project.agile.solution.task.intent"].with_user(manager).create(values)
        )
        env.cr.commit()
        proposal = {"uid": manager.id, "intent_id": intent.id, "action": "confirm"}
        result = race(env, proposal, proposal)
        assert intent.state == "consumed"
        assert (
            env["project.agile.requirement.task.link"].search_count(
                [("task_id", "=", intent.task_id.id)]
            )
            == 1
        )
        assert env["project.task"].search_count([("name", "=", values["name"])]) == (
            1 if operation == "create" else 0
        )
        results.append({"operation": operation, "workers": result})
    working = revision.browse(revision.requirement_id.action_new_revision()["res_id"])
    pending = (
        env["project.agile.solution.task.intent"]
        .with_user(manager)
        .create(
            {
                **values,
                "operation": "create",
                "task_id": False,
                "name": "SYNTHETIC stale concurrent preview",
                "requirement_revision_ids": [Command.set(working.ids)],
            }
        )
    )
    count = env["project.task"].search_count([])
    env.cr.commit()
    common = {"uid": manager.id, "intent_id": pending.id}
    stale = race(
        env,
        {**common, "action": "edit_requirement"},
        {
            **common,
            "action": "confirm",
            "expect_stale": True,
        },
    )
    assert pending.state == "preview" and not pending.task_id and not working.sealed
    assert env["project.task"].search_count([]) == count
    assert not env["project.agile.requirement.task.link"].search_count(
        [
            ("requirement_revision_id", "=", working.id),
        ]
    )
    results.append({"operation": "stale_source", "workers": stale})
    # Stdout is the canonical verifier's result ABI, not an application log.
    print(  # pylint: disable=print-used
        "M8_TASK_INTENT_CONCURRENCY_OK "
        + json.dumps({"races": results}, sort_keys=True),
        flush=True,
    )

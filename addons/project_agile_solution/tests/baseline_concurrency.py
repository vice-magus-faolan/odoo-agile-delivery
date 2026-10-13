"""Independent PostgreSQL transactions prove allocation and approval serialization.

Only called by the canonical disposable isolated-install source probe. Explicit
commits and subprocesses belong to this owned fixture, never business methods.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from psycopg2.errors import SerializationFailure

from odoo import Command
from odoo.exceptions import ValidationError

from odoo.addons.mail.tests.common import mail_new_test_user


def _wait(path):
    deadline = time.monotonic() + 30
    while not path.exists():
        if time.monotonic() >= deadline:
            raise AssertionError("Missing baseline race rendezvous: " + path.name)
        time.sleep(0.02)


def worker(env):
    """A contender retries serialization only in a completely fresh transaction."""
    data = json.loads(os.environ["SOLUTION_BASELINE_RACE"])
    assert env.cr.dbname == "odoo_agile_verify_install"
    directory, name = Path(data["directory"]), data["worker"]
    revision = (
        env["project.agile.solution.revision"]
        .with_user(data["uid"])
        .browse(data["revision_id"])
    )
    revision.read(["state", "number"])  # Both contenders establish old snapshots.
    env.cr.execute("SELECT pg_backend_pid()")
    backend = env.cr.fetchone()[0]
    (directory / (name + ".ready")).touch()
    _wait(directory / (name + ".go"))
    retries, outcome = 0, None
    while retries < 3:
        (directory / (name + ".attempt")).touch()
        try:
            if data["action"] == "successor":
                revision.action_new_revision()
            else:
                revision.action_approve()
            outcome = "applied"
            if name == "winner":
                (directory / "winner.mutated").touch()
                _wait(directory / "winner.commit")
            env.cr.commit()
            break
        except SerializationFailure:
            env.cr.rollback()
            env.invalidate_all()
            revision = (
                env["project.agile.solution.revision"]
                .with_user(data["uid"])
                .browse(data["revision_id"])
            )
            retries += 1
        except ValidationError:
            env.cr.rollback()
            outcome = "stale_rejected"
            break
    assert outcome, "Retry bound exhausted"
    (directory / (name + ".json")).write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "backend": backend,
                "retries": retries,
                "outcome": outcome,
            }
        )
    )


def _launch(env, directory, name, revision, uid, action):
    data = {
        "directory": str(directory),
        "worker": name,
        "revision_id": revision.id,
        "uid": uid,
        "action": action,
    }
    command = [
        "odoo",
        "shell",
        "--config=/etc/odoo/odoo.conf",
        "--database",
        env.cr.dbname,
        "--no-http",
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "SOLUTION_BASELINE_RACE": json.dumps(data)},
    )
    assert process.stdin is not None
    process.stdin.write(
        "from odoo.addons.project_agile_solution.tests.baseline_concurrency "
        "import worker\nworker(env)\n"
    )
    process.stdin.close()
    process.stdin = None
    return process


def _race(env, revision, uid, action):
    with tempfile.TemporaryDirectory(
        prefix="solution-baseline-race-", dir="/var/lib/odoo"
    ) as temporary:
        directory, processes = Path(temporary), []
        try:
            for name in ("winner", "loser"):
                processes.append(_launch(env, directory, name, revision, uid, action))
            for name in ("winner", "loser"):
                _wait(directory / (name + ".ready"))
            (directory / "winner.go").touch()
            _wait(directory / "winner.mutated")
            (directory / "loser.go").touch()
            _wait(directory / "loser.attempt")
            (directory / "winner.commit").touch()
            for process in processes:
                stdout, stderr = process.communicate(timeout=40)
                assert process.returncode == 0, (stdout, stderr)
            results = [
                json.loads((directory / (name + ".json")).read_text())
                for name in ("winner", "loser")
            ]
            assert results[0]["pid"] != results[1]["pid"]
            assert results[0]["backend"] != results[1]["backend"]
            assert results[0]["outcome"] == "applied"
            assert results[1]["outcome"] == "stale_rejected"
            assert results[1]["retries"] == 1
            return {"action": action, "workers": results}
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)


def run_probe(env):
    """Create only synthetic isolated DB records and verify durable race outcomes."""
    assert env.cr.dbname == "odoo_agile_verify_install"
    manager = mail_new_test_user(
        env,
        "solution_race_manager",
        groups="project.group_project_manager",
        company_id=env.company.id,
        company_ids=[Command.set(env.company.ids)],
    )
    project = env["project.project"].create(
        {
            "name": "SYNTHETIC baseline race",
            "agile_enabled": True,
            "agile_key": "M8RACE",
            "company_id": env.company.id,
            "privacy_visibility": "employees",
        }
    )
    solution = (
        env["project.agile.solution"]
        .with_user(manager)
        .create({"name": "SYNTHETIC race lineage", "project_id": project.id})
    )
    document = (
        env["project.agile.solution.document"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC race spec",
                "solution_id": solution.id,
                "approver_id": manager.id,
            }
        )
    )
    baseline = (
        env["project.agile.solution.revision"]
        .with_user(manager)
        .create(
            {
                "document_id": document.id,
                "title": "SYNTHETIC v1",
                "section_ids": [
                    Command.create(
                        {"title": "Frozen scope", "body": "<p>v1 actual content</p>"}
                    )
                ],
            }
        )
    )
    baseline.action_submit()
    baseline.action_approve()
    frozen = baseline.action_read_snapshot()["snapshot_json"]
    env.cr.commit()
    allocation = _race(env, baseline, manager.id, "successor")
    env.cr.rollback()
    env.invalidate_all()
    revisions = (
        env["project.agile.solution.revision"]
        .with_user(manager)
        .search([("document_id", "=", document.id)], order="number")
    )
    assert len(revisions) == 2 and revisions.mapped("number") == [1, 2]
    assert revisions[0].state == "approved" and revisions[1].state == "draft"
    assert revisions[0].action_read_snapshot()["snapshot_json"] == frozen
    revisions[1].action_submit()
    env.cr.commit()
    approval = _race(env, revisions[1], manager.id, "approve")
    env.cr.rollback()
    env.invalidate_all()
    assert revisions[0].state == "superseded" and revisions[1].state == "approved"
    assert revisions[0].action_read_snapshot()["snapshot_json"] == frozen
    # Stdout is the canonical verifier's result ABI, not an application log.
    print(  # pylint: disable=print-used
        "M8_BASELINE_CONCURRENCY_OK "
        + json.dumps(
            {
                "allocation": allocation,
                "approval": approval,
                "revision_count": 2,
                "v1_content_unchanged": True,
            },
            sort_keys=True,
        ),
        flush=True,
    )

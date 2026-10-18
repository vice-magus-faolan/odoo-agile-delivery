"""Independent transactions exercise stable key and content revision allocation.

This is a disposable fixture producer, never business code. Rendezvous files and
commits are confined to the canonical isolated install database/container.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from baseline_concurrency import _wait
from psycopg2.errors import SerializationFailure

from odoo import Command
from odoo.exceptions import ConcurrencyError, ValidationError

from odoo.addons.mail.tests.common import mail_new_test_user

IDENTITIES = {
    "requirement": "project.agile.requirement",
    "context": "project.agile.solution.context",
}


def worker(env):
    data = json.loads(os.environ["SOLUTION_CONTENT_RACE"])
    assert env.cr.dbname == "odoo_agile_verify_install"
    directory, name = Path(data["directory"]), data["worker"]
    identities = env[IDENTITIES[data["kind"]]].with_user(data["uid"])
    identity = identities.browse(data["identity_id"])
    identity.read(["key"])  # Establish the stale repeatable-read snapshot.
    env.cr.execute("SELECT pg_backend_pid()")
    backend = env.cr.fetchone()[0]
    (directory / (name + ".ready")).touch()
    _wait(directory / (name + ".go"))
    retries, outcome, result_id = 0, None, None
    while retries < 3:
        (directory / (name + ".attempt")).touch()
        try:
            if data["action"] == "key":
                result = identities.create(
                    {
                        "name": "SYNTHETIC concurrent intent",
                        "solution_id": data["solution_id"],
                    }
                )
            else:
                values = identity._complete_revisions()[-1]._copy_content_values()
                values[identity._identity_field] = identity.id
                result = (
                    env[identity._revision_model].with_user(data["uid"]).create(values)
                )
            result_id = result.id
            outcome = "applied"
            if name == "winner":
                (directory / "winner.mutated").touch()
                _wait(directory / "winner.commit")
            env.cr.commit()
            break
        except (SerializationFailure, ConcurrencyError):
            env.cr.rollback()
            env.invalidate_all()
            identities = env[IDENTITIES[data["kind"]]].with_user(data["uid"])
            identity = identities.browse(data["identity_id"])
            retries += 1
            time.sleep(0.1)
        except ValidationError:
            env.cr.rollback()
            outcome = "stale_rejected"
            break
    assert outcome, "Content allocation retry bound exhausted"
    (directory / (name + ".json")).write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "backend": backend,
                "retries": retries,
                "outcome": outcome,
                "result_id": result_id,
            }
        )
    )


def _launch(env, directory, name, identity, manager, action, kind):
    data = {
        "directory": str(directory),
        "worker": name,
        "identity_id": identity.id,
        "solution_id": identity.solution_id.id,
        "uid": manager.id,
        "action": action,
        "kind": kind,
    }
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
        env={**os.environ, "SOLUTION_CONTENT_RACE": json.dumps(data)},
    )
    assert process.stdin is not None
    process.stdin.write(
        "import sys\nsys.path.insert(0, '/mnt/policy-tests')\n"
        "from requirement_concurrency "
        "import worker\nworker(env)\n"
    )
    process.stdin.close()
    process.stdin = None
    return process


def _race(env, identity, manager, action, kind):
    with tempfile.TemporaryDirectory(
        prefix="solution-content-race-", dir="/var/lib/odoo"
    ) as temporary:
        directory, processes = Path(temporary), []
        try:
            for name in ("winner", "loser"):
                processes.append(
                    _launch(env, directory, name, identity, manager, action, kind)
                )
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
            assert (
                results[0]["pid"] != results[1]["pid"]
                and results[0]["backend"] != results[1]["backend"]
            )
            assert results[0]["outcome"] == "applied"
            assert results[1]["outcome"] == (
                "applied" if action == "key" else "stale_rejected"
            )
            assert results[1]["retries"] >= 1
            if action == "key":
                records = (
                    env[IDENTITIES[kind]]
                    .with_user(manager)
                    .browse([row["result_id"] for row in results])
                )
                env.cr.rollback()
                env.invalidate_all()
                assert len(set(records.mapped("key"))) == 2
            return {"kind": kind, "action": action, "workers": results}
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)


def run_probe(env):
    assert env.cr.dbname == "odoo_agile_verify_install"
    manager = mail_new_test_user(
        env,
        "solution_content_race_manager",
        groups="project.group_project_manager",
        company_id=env.company.id,
        company_ids=[Command.set(env.company.ids)],
    )
    project = env["project.project"].create(
        {
            "name": "SYNTHETIC content races",
            "agile_enabled": True,
            "agile_key": "M8CONTENTRACE",
            "company_id": env.company.id,
            "privacy_visibility": "employees",
        }
    )
    solution = (
        env["project.agile.solution"]
        .with_user(manager)
        .create({"name": "SYNTHETIC content races", "project_id": project.id})
    )
    requirement = (
        env["project.agile.requirement"]
        .with_user(manager)
        .create({"name": "SYNTHETIC FR", "solution_id": solution.id})
    )
    requirement_revision = (
        env["project.agile.requirement.revision"]
        .with_user(manager)
        .create(
            {
                "requirement_id": requirement.id,
                "title": "SYNTHETIC initial intent",
                "description": "Bounded outcome",
                "rationale": "Evidence",
                "verification_method": "Synthetic negative matrix",
                "acceptance_expectations": "Reject foreign identities",
            }
        )
    )
    context = (
        env["project.agile.solution.context"]
        .with_user(manager)
        .create(
            {"name": "SYNTHETIC domain", "kind": "domain", "solution_id": solution.id}
        )
    )
    context_revision = (
        env["project.agile.solution.context.revision"]
        .with_user(manager)
        .create({"context_id": context.id, "title": "SYNTHETIC domain context"})
    )
    document = (
        env["project.agile.solution.document"]
        .with_user(manager)
        .create({"name": "SYNTHETIC race brief", "solution_id": solution.id})
    )
    baseline = (
        env["project.agile.solution.revision"]
        .with_user(manager)
        .create(
            {
                "document_id": document.id,
                "title": document.name,
                "requirement_revision_ids": [Command.set(requirement_revision.ids)],
                "context_revision_ids": [Command.set(context_revision.ids)],
            }
        )
    )
    baseline.action_submit()
    baseline.action_approve()
    frozen = baseline.action_read_snapshot()["snapshot_json"]
    env.cr.commit()
    results = []
    for kind, identity in (("requirement", requirement), ("context", context)):
        for action in ("key", "revision"):
            results.append(_race(env, identity, manager, action, kind))
            env.cr.rollback()
            env.invalidate_all()
        revisions = identity._complete_revisions()
        assert (
            revisions.mapped("number") == [1, 2]
            and revisions[0].sealed
            and not revisions[1].sealed
        )
    assert baseline.action_read_snapshot()["snapshot_json"] == frozen
    # Stdout is the canonical verifier's result ABI, not an application log.
    print(  # pylint: disable=print-used
        "M8_REQUIREMENT_CONTEXT_CONCURRENCY_OK "
        + json.dumps({"races": results, "v1_content_unchanged": True}, sort_keys=True),
        flush=True,
    )

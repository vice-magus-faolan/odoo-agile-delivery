"""Actual independent-process duplicate association/provenance continuity regression."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

assert env.cr.dbname == "odoo_agile_verify_install"
project = env["project.project"].create(
    {
        "name": "Association race",
        "company_id": env.company.id,
        "privacy_visibility": "employees",
        "agile_enabled": True,
        "agile_key": "ARACE",
    }
)
task = env["project.task"].create(
    {"name": "Association race task", "project_id": project.id}
)
repository = env["project.git.repository"].create(
    {
        "name": "Association race",
        "project_id": project.id,
        "provider": "github",
        "provider_repository_id": "association-race",
        "canonical_url": "https://github.com/synthetic/association-race",
    }
)
deliveries = env["project.git.delivery"].create(
    [
        {
            "repository_id": repository.id,
            "provider_delivery_id": name,
            "event_type": "pull_request",
            "payload_sha256": "a" * 64,
            "payload_size": 1,
            "state": "queued",
        }
        for name in ("winner", "loser")
    ]
)
before = task.read(["stage_id", "state", "write_date", "message_ids"])[0]
env.cr.commit()
source = Path("/mnt/policy-tests/github_association_concurrency_worker.py").read_text()
command = [
    "odoo",
    "shell",
    "--config=/etc/odoo/odoo.conf",
    "--database",
    env.cr.dbname,
    "--no-http",
]


def wait(directory, name):
    deadline = time.monotonic() + 20
    while not (directory / name).exists():
        assert time.monotonic() < deadline, (
            "Missing association race rendezvous " + name
        )
        time.sleep(0.02)


def launch(directory, name, delivery):
    data = {
        "directory": str(directory),
        "worker": name,
        "delivery_id": delivery.id,
        "task_id": task.id,
        "agile_key": task.agile_key,
    }
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "GITHUB_ASSOCIATION_SCENARIO": json.dumps(data)},
    )
    process.stdin.write(source)
    process.stdin.close()
    process.stdin = None
    return process


def finish(directory, name, process):
    stdout, stderr = process.communicate(timeout=30)
    assert process.returncode == 0, (name, stdout, stderr)
    return json.loads((directory / (name + ".json")).read_text())


with tempfile.TemporaryDirectory(prefix="github-association-race-") as temporary:
    directory = Path(temporary)
    processes = []
    try:
        winner = launch(directory, "winner", deliveries[0])
        processes.append(winner)
        loser = launch(directory, "loser", deliveries[1])
        processes.append(loser)
        wait(directory, "winner.ready")
        wait(directory, "loser.ready")
        (directory / "winner.go").touch()
        winning = finish(directory, "winner", winner)
        (directory / "loser.go").touch()
        losing = finish(directory, "loser", loser)
        assert (
            winning["pid"] != losing["pid"] and winning["backend"] != losing["backend"]
        )
        assert winning["restarts"] == 0 and losing["restarts"] == 1
        assert losing["rolled_back_delivery_has_no_audit"]
        assert (
            winning["outcome"] == "associated"
            and losing["outcome"] == "already_associated"
        )
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
env.cr.rollback()
env.invalidate_all()
links = env["project.git.task.association"].search(
    [("repository_id", "=", repository.id)]
)
audits = env["project.git.association.audit"].search(
    [("repository_id", "=", repository.id)]
)
assert len(links) == 1 and links.task_id == task
assert len(audits) == 2 and audits.task_id == task
assert set(audits.mapped("delivery_id").ids) == set(deliveries.ids)
assert before == task.read(["stage_id", "state", "write_date", "message_ids"])[0]
# Stdout is this disposable probe's machine-readable result ABI.
print(  # pylint: disable=print-used
    "GITHUB_ASSOCIATION_CONCURRENCY="
    + json.dumps(
        {
            "scenario": "duplicate_association_fresh_transaction_proof",
            "workers": [winning, losing],
            "association_count": len(links),
            "audit_count": len(audits),
            "task_unchanged": True,
        },
        sort_keys=True,
    ),
    flush=True,
)

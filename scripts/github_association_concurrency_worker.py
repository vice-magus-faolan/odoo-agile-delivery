"""Independent normalizer association-race worker; disposable DB only."""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

from psycopg2 import IntegrityError
from psycopg2.errors import SerializationFailure

assert env.cr.dbname == "odoo_agile_verify_install"
data = json.loads(os.environ["GITHUB_ASSOCIATION_SCENARIO"])
directory = Path(data["directory"])
name = data["worker"]
model = env["project.git.task.association"]
original = type(model).search
lookups = []


def paused_search(records, domain, *args, **kwargs):
    result = original(records, domain, *args, **kwargs)
    lookups.append(bool(result))
    if len(lookups) == 1:
        assert not result
        (directory / (name + ".ready")).touch()
        deadline = time.monotonic() + 20
        while not (directory / (name + ".go")).exists():
            assert time.monotonic() < deadline, "Association race rendezvous timed out"
            time.sleep(0.02)
    return result


def associate():
    delivery = env["project.git.delivery"].browse(data["delivery_id"])
    delivery._associate_agile_key(
        "pull_request", "race-source", "title", data["agile_key"]
    )


env.cr.execute("SELECT pg_backend_pid()")
backend = env.cr.fetchone()[0]
restarts = 0
rolled_back_delivery_has_no_audit = None
try:
    with patch.object(type(model), "search", paused_search):
        associate()
except (IntegrityError, SerializationFailure):
    # PostgreSQL repeatable-read may hide the committed winner. Never turn this
    # transaction's constraint exception into proof; restart the whole test cursor.
    env.cr.rollback()
    env.invalidate_all()
    restarts += 1
    assert not env["project.git.association.audit"].search(
        [("delivery_id", "=", data["delivery_id"])]
    )
    rolled_back_delivery_has_no_audit = True
    associate()

audit = env["project.git.association.audit"].search(
    [("delivery_id", "=", data["delivery_id"])]
)
assert len(audit) == 1 and audit.task_id.id == data["task_id"]
assert audit.agile_key == data["agile_key"]
assert audit.outcome == ("already_associated" if restarts else "associated")
env.cr.commit()
(directory / (name + ".json")).write_text(
    json.dumps(
        {
            "worker": name,
            "pid": os.getpid(),
            "backend": backend,
            "restarts": restarts,
            "audit_task_id": audit.task_id.id,
            "outcome": audit.outcome,
            "initial_lookup_empty": lookups[0] is False,
            "rolled_back_delivery_has_no_audit": rolled_back_delivery_has_no_audit,
        }
    )
)

"""Verify competing replay transactions after Odoo registry preload returns."""

import json
import threading
from uuid import uuid4

from odoo import SUPERUSER_ID, api
from odoo.service.model import retrying

assert env.cr.dbname == "odoo_agile_verify_install"
registry = env.registry
unique_key = uuid4().hex[:8].upper()
evidence_fields = [
    "repository_id",
    "provider_delivery_id",
    "event_type",
    "payload_sha256",
    "payload_size",
    "state",
    "received_at",
    "retained_payload",
]
with registry._db.cursor() as cursor:
    environment = api.Environment(cursor, SUPERUSER_ID, {})
    project = environment["project.project"].create(
        {
            "name": "Concurrent replay " + unique_key,
            "privacy_visibility": "employees",
            "agile_enabled": True,
            "agile_key": "CR" + unique_key,
        }
    )
    repository = environment["project.git.repository"].create(
        {
            "name": "Concurrent replay",
            "provider": "github",
            "provider_repository_id": "replay-" + unique_key,
            "canonical_url": "https://github.com/acme/replay",
            "project_id": project.id,
        }
    )
    assert "git_policy_evidence_version" in repository._fields
    values = {
        "repository_id": repository.id,
        "provider_delivery_id": "concurrent-delivery",
        "event_type": "push",
        "payload_sha256": "a" * 64,
        "payload_size": 2,
    }
    delivery, created = environment[
        "project.git.delivery"
    ]._record_authenticated_github_delivery(**values)
    assert created
    delivery_id = delivery.id
    project_id, repository_id = project.id, repository.id
    before = delivery.read(evidence_fields)
    cursor.commit()

ready = threading.Barrier(2)
results, failures, workers = [], [], []


def record_replay():
    """Own a separate session and let native retrying restart stale work."""
    try:
        with registry._db.cursor() as cursor:
            environment = api.Environment(cursor, SUPERUSER_ID, {})
            cursor.execute("SELECT pg_backend_pid()")
            worker = {"backend": cursor.fetchone()[0], "attempts": 0}
            workers.append(worker)
            assert (
                environment["project.git.delivery"]
                .browse(delivery_id)
                .replay_mismatch_count
                == 0
            )
            ready.wait(timeout=5)

            def record():
                worker["attempts"] += 1
                cursor.execute("SET LOCAL lock_timeout = %s", ("3s",))
                cursor.execute("SET LOCAL statement_timeout = %s", ("10s",))
                replay, created, exact = environment[
                    "project.git.delivery"
                ]._record_authenticated_github_delivery(
                    **{**values, "payload_sha256": "b" * 64},
                    return_replay_status=True,
                )
                return replay.id, created, exact

            results.append(retrying(record, environment))
    except BaseException as error:
        failures.append(error)


threads = [threading.Thread(target=record_replay, daemon=True) for _ in range(2)]
try:
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    assert not any(thread.is_alive() for thread in threads), "Replay worker timed out"
    assert not failures, failures
    assert results == [(delivery_id, False, False)] * 2, results
    assert len(workers) == 2 and workers[0]["backend"] != workers[1]["backend"]
    assert sorted(worker["attempts"] for worker in workers) == [1, 2], workers
    with registry._db.cursor() as cursor:
        environment = api.Environment(cursor, SUPERUSER_ID, {})
        deliveries = environment["project.git.delivery"].search(
            [("repository_id", "=", repository_id)]
        )
        assert deliveries.ids == [delivery_id]
        assert deliveries.replay_mismatch_count == 2
        assert deliveries.last_replay_mismatch_at
        assert deliveries.read(evidence_fields) == before
        result = {
            "workers": workers,
            "delivery_count": len(deliveries),
            "replay_mismatch_count": deliveries.replay_mismatch_count,
            "last_replay_mismatch_at": str(deliveries.last_replay_mismatch_at),
            "original_evidence_unchanged": True,
        }
finally:
    # Each cursor belongs to its worker; do not close a live transaction here.
    for thread in threads:
        if thread.ident is not None:
            thread.join(60)
    assert not any(thread.is_alive() for thread in threads), "Replay cleanup blocked"
    with registry._db.cursor() as cursor:
        environment = api.Environment(cursor, SUPERUSER_ID, {})
        repository = environment["project.git.repository"].browse(repository_id)
        repository.git_delivery_ids.unlink()
        repository.unlink()
        environment["project.project"].browse(project_id).unlink()
        cursor.commit()

# Stdout is this disposable probes machine-readable result ABI.
print(  # pylint: disable=print-used
    "GITHUB_INGRESS_REPLAY_CONCURRENCY=" + json.dumps(result, sort_keys=True),
    flush=True,
)

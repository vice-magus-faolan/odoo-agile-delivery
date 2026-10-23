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
from odoo.exceptions import AccessError, ConcurrencyError, ValidationError

from odoo.addons.mail.tests.common import mail_new_test_user

SOURCE_OWNER_CHANGES = {
    "portal_solution_archive": ("solution", "active"),
    "portal_project_archive": ("project", "active"),
    "portal_agile_disable": ("project", "agile_enabled"),
}


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
    if data.get("publication_id"):
        env["project.agile.solution.portal.publication"].with_user(
            data["client_uid"]
        ).browse(data["publication_id"]).read(["name"])
    else:
        revision.read(["state", "number"])  # Both contenders establish old snapshots.
    env.cr.execute("SELECT pg_backend_pid()")
    backend = env.cr.fetchone()[0]
    (directory / (name + ".ready")).touch()
    _wait(directory / (name + ".go"))
    retries, outcome, first_conflict = 0, None, None
    while retries < 3:
        (directory / (name + ".attempt")).touch()
        try:
            if data.get("publication_id"):
                _portal_apply(env, data)
            elif data["action"] == "successor":
                revision.action_new_revision()
            elif data["action"] == "edit_section":
                revision.section_ids.write(
                    {"body": "<p>SYNTHETIC concurrent narrative</p>"}
                )
            elif data["action"] == "submit":
                revision.action_submit()
            else:
                revision.action_approve()
            outcome = "applied"
            (directory / (name + ".observed")).touch()
            if name == "winner":
                (directory / "winner.mutated").touch()
                _wait(directory / "winner.commit")
            env.cr.commit()
            break
        except (SerializationFailure, ConcurrencyError) as error:
            if first_conflict is None:
                first_conflict = type(error).__name__
            env.cr.rollback()
            env.invalidate_all()
            revision = (
                env["project.agile.solution.revision"]
                .with_user(data["uid"])
                .browse(data["revision_id"])
            )
            retries += 1
            (directory / (name + ".observed")).touch()
            if name == "loser" and data.get("publication_id"):
                # Keep the real first overlap conflict, then retry after commit.
                _wait(directory / "winner.json")
            time.sleep(0.1)
        except (AccessError, ValidationError):
            env.cr.rollback()
            outcome = "stale_rejected"
            (directory / (name + ".observed")).touch()
            break
    assert outcome, "Retry bound exhausted"
    (directory / (name + ".json")).write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "backend": backend,
                "retries": retries,
                "first_conflict": first_conflict,
                "outcome": outcome,
            }
        )
    )


def _launch(env, directory, name, revision, uid, action, portal=None):
    data = {
        "directory": str(directory),
        "worker": name,
        "revision_id": revision.id,
        "uid": uid,
        "action": action,
    }
    data.update(portal or {})
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
        "import sys\nsys.path.insert(0, '/mnt/probes')\n"
        "from baseline_concurrency "
        "import worker\nworker(env)\n"
    )
    process.stdin.close()
    process.stdin = None
    return process


def _race(env, revision, uid, action, *, portal=None, ordering="overlap"):
    with tempfile.TemporaryDirectory(
        prefix="solution-baseline-race-", dir="/var/lib/odoo"
    ) as temporary:
        directory, processes = Path(temporary), []
        try:
            for name in ("winner", "loser"):
                selected = (
                    action[0 if name == "winner" else 1]
                    if isinstance(action, tuple)
                    else action
                )
                processes.append(
                    _launch(env, directory, name, revision, uid, selected, portal)
                )
            for name in ("winner", "loser"):
                _wait(directory / (name + ".ready"))
            (directory / "winner.go").touch()
            _wait(directory / "winner.mutated")
            if ordering == "committed":
                (directory / "winner.commit").touch()
                _wait(directory / "winner.json")
            (directory / "loser.go").touch()
            # Portal overlap is controlled through the actual first result, not
            # merely entry into the action before the winner is allowed to commit.
            _wait(directory / ("loser.observed" if portal else "loser.attempt"))
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
            assert results[1]["outcome"] == (
                "applied"
                if isinstance(action, tuple) and not portal
                else "stale_rejected"
            )
            assert results[1]["retries"] >= 1
            if portal and action[0] in SOURCE_OWNER_CHANGES:
                assert results[0]["retries"] == 0
                assert results[1]["retries"] == 1
                assert results[1]["first_conflict"] == (
                    "SerializationFailure"
                    if ordering == "committed"
                    else "ConcurrencyError"
                ), results
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
    working = revisions[1].browse(revisions[1].action_new_revision()["res_id"])
    env.cr.commit()
    narrative = _race(env, working, manager.id, ("edit_section", "submit"))
    env.cr.rollback()
    env.invalidate_all()
    assert working.state == "review"
    assert (
        "SYNTHETIC concurrent narrative"
        in working.action_read_snapshot()["snapshot_json"]
    )
    assert revisions[0].action_read_snapshot()["snapshot_json"] == frozen
    portal = run_portal_probe(env)
    # Stdout is the canonical verifier's result ABI, not an application log.
    print(  # pylint: disable=print-used
        "M8_BASELINE_CONCURRENCY_OK "
        + json.dumps(
            {
                "portal": portal,
                "allocation": allocation,
                "approval": approval,
                "narrative_submission": narrative,
                "revision_count": len(document._complete_revisions()),
                "v1_content_unchanged": True,
            },
            sort_keys=True,
        ),
        flush=True,
    )


def _portal_apply(env, data):
    publication = env["project.agile.solution.portal.publication"].browse(
        data["publication_id"]
    )
    client = env["res.users"].browse(data["client_uid"])
    action = data["action"]
    if action == "portal_document":
        publication.with_user(client).action_decide_document("approved")
    elif action == "portal_requirement":
        publication.with_user(client).action_decide_requirement(
            data["key"],
            data["number"],
            "accepted",
            "Identity matrix",
            "Actual fixture observation",
        )
    elif action == "portal_issue":
        publication.revision_id.with_user(data["manager_uid"]).with_context(
            allowed_company_ids=data["allowed_company_ids"]
        ).action_issue_portal(client.id)
    elif action in SOURCE_OWNER_CHANGES:
        owner, field = SOURCE_OWNER_CHANGES[action]
        source = (
            publication.revision_id.solution_id
            if owner == "solution"
            else publication.project_id
        )
        source.with_user(data["manager_uid"]).write({field: False})
    elif action == "portal_revoke":
        publication.with_user(data["manager_uid"]).action_revoke()
    elif action == "portal_follower":
        publication.project_id.message_unsubscribe(partner_ids=client.partner_id.ids)
    elif action == "portal_group":
        env.ref("base.group_portal").write({"user_ids": [Command.unlink(client.id)]})
    elif action == "portal_implication":
        env["res.groups"].browse(data["group_id"]).write(
            {"implied_ids": [Command.clear()]}
        )
    elif action == "portal_company":
        env["res.company"].browse(data["company_id"]).write(
            {"user_ids": [Command.unlink(client.id)]}
        )
    elif action == "portal_supersede":
        env["project.agile.solution.revision"].with_user(data["manager_uid"]).browse(
            data["successor_id"]
        ).action_approve()
    else:
        raise AssertionError("Unknown portal fixture action")
    env.flush_all()


def _portal_fixture(
    env,
    manager,
    project,
    solution,
    requirement,
    secondary,
    suffix,
    *,
    implication=False,
):
    """An otherwise-valid designated signer and internally approved publication."""
    client = mail_new_test_user(
        env,
        "solution_race_" + suffix,
        groups="base.group_portal",
        company_id=secondary.id,
        company_ids=[Command.set((project.company_id | secondary).ids)],
    )
    project.message_subscribe(partner_ids=client.partner_id.ids)
    document = (
        env["project.agile.solution.document"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC " + suffix,
                "solution_id": solution.id,
                "portal_approver_id": client.id,
                "approver_id": manager.id,
            }
        )
    )
    revision = (
        env["project.agile.solution.revision"]
        .with_user(manager)
        .create(
            {
                "document_id": document.id,
                "title": "SYNTHETIC portal race",
                "requirement_revision_ids": [Command.set(requirement.ids)],
            }
        )
    )
    revision.action_submit()
    revision.action_approve()
    metadata = {
        "client_uid": client.id,
        "key": requirement.requirement_id.key,
        "number": requirement.number,
        "manager_uid": manager.id,
        "company_id": project.company_id.id,
        "allowed_company_ids": (project.company_id | secondary).ids,
        "requirement_id": requirement.id,
        "requirement_head_id": requirement.sudo()._last_acceptance_id.id,
    }
    if implication:
        group = env["res.groups"].create(
            {
                "name": "SYNTHETIC portal implication " + suffix,
                "implied_ids": [Command.link(env.ref("base.group_portal").id)],
            }
        )
        client.write({"group_ids": [Command.link(group.id)]})
        metadata["group_id"] = group.id
    metadata["publication_id"] = revision.with_context(
        allowed_company_ids=metadata["allowed_company_ids"]
    ).action_issue_portal(client.id)
    return revision, metadata


def _check_source_owner_result(env, revision, metadata, action, loser_action):
    """Archive hides, but does not revoke or mutate grants/receipts on losing work."""
    publication = env["project.agile.solution.portal.publication"].browse(
        metadata["publication_id"]
    )
    grants = env["project.agile.solution.portal.publication"].search(
        [("revision_id", "=", revision.id)]
    )
    assert grants == publication
    assert not publication.revoked_at and not publication.revoked_by_id
    assert not publication._decision_head_id and not publication._requirement_head_id
    requirement = env["project.agile.requirement.revision"].browse(
        metadata["requirement_id"]
    )
    assert requirement._last_acceptance_id.id == metadata["requirement_head_id"]
    for model in (
        "project.agile.solution.portal.document.decision",
        "project.agile.requirement.acceptance",
    ):
        assert not env[model].search_count([("publication_id", "=", publication.id)])
    owner, field = SOURCE_OWNER_CHANGES[action]
    source = revision.solution_id if owner == "solution" else revision.project_id
    assert not source[field]
    # A genuinely fresh disabled-owner transaction must reject the same action.
    rejected = False
    try:
        with env.cr.savepoint():
            _portal_apply(env, {**metadata, "action": loser_action})
    except (AccessError, ValidationError):
        rejected = True
    assert rejected, "Disabled source owner accepted fresh portal work"
    source.with_user(metadata["manager_uid"]).write({field: True})
    env.flush_all()
    assert not publication.revoked_at
    assert publication.with_user(metadata["client_uid"]).action_view()["can_decide"]
    # Restoration is a committed native mutation, not a new grant or republish.
    env.cr.commit()
    for selected in ("portal_document", "portal_requirement", "portal_issue"):
        with env.cr.savepoint() as savepoint:
            _portal_apply(env, {**metadata, "action": selected})
            savepoint.rollback()


def run_portal_probe(env):
    from task_concurrency import seed

    manager, project, solution, requirement = seed(env, "M8PORTALRACE")
    requirement.write({"audience": "customer"})
    project.write({"privacy_visibility": "portal"})
    secondary = env["res.company"].create({"name": "SYNTHETIC portal race secondary"})
    manager.write({"company_ids": [Command.set((project.company_id | secondary).ids)]})
    results = []
    actions = (
        "portal_document",
        "portal_requirement",
        "portal_revoke",
        "portal_follower",
        "portal_group",
        "portal_implication",
        "portal_company",
        "portal_supersede",
        *SOURCE_OWNER_CHANGES,
    )
    for action in actions:
        loser_actions = (
            ("portal_document", "portal_requirement", "portal_issue")
            if action in SOURCE_OWNER_CHANGES
            else (
                "portal_requirement"
                if action == "portal_requirement"
                else "portal_document",
            )
        )
        for ordering in ("overlap", "committed"):
            for loser_action in loser_actions:
                revision, metadata = _portal_fixture(
                    env,
                    manager,
                    project,
                    solution,
                    requirement,
                    secondary,
                    action + ordering + loser_action,
                    implication=action == "portal_implication",
                )
                if action == "portal_supersede":
                    successor = revision.browse(
                        revision.action_new_revision()["res_id"]
                    )
                    successor.action_submit()
                    metadata["successor_id"] = successor.id
                # Both contenders must be valid before imposing either ordering.
                for selected in (loser_action, action):
                    with env.cr.savepoint() as savepoint:
                        _portal_apply(env, {**metadata, "action": selected})
                        savepoint.rollback()
                env.cr.commit()
                result = _race(
                    env,
                    revision,
                    env.uid,
                    (action, loser_action),
                    portal=metadata,
                    ordering=ordering,
                )
                env.cr.rollback()
                env.invalidate_all()
                expected = (
                    1 if action in ("portal_document", "portal_requirement") else 0
                )
                model = (
                    "project.agile.requirement.acceptance"
                    if action == "portal_requirement"
                    else "project.agile.solution.portal.document.decision"
                )
                assert (
                    env[model].search_count(
                        [("publication_id", "=", metadata["publication_id"])]
                    )
                    == expected
                )
                if action in SOURCE_OWNER_CHANGES:
                    _check_source_owner_result(
                        env, revision, metadata, action, loser_action
                    )
                results.append(
                    {
                        "action": action,
                        "loser": loser_action,
                        "ordering": ordering,
                        "workers": result,
                    }
                )
    return results

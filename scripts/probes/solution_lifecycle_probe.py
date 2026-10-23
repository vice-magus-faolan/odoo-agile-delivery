"""Persisted-data optional M8 lifecycles, only in the declared disposable DB.

Canonical verify supplies a closed PHASE literal before this stdin source.
Commits belong exclusively to this owned fixture, never business methods.
Uninstall destroys M8 history; these checks do not promise archival retention.
"""

import json
import sys

sys.path.insert(0, "/mnt/probes")

from datetime import date, datetime

from odoo import Command

DATABASE = (
    "odoo_agile_verify_upgrade"
    if PHASE.endswith("legacy_proxy")
    else "odoo_agile_verify_install"
)
KEY = (
    "m8.disposable.lifecycle.legacy.fixture"
    if PHASE.endswith("legacy_proxy")
    else "m8.disposable.lifecycle.fixture"
)
NATIVE_FIELDS = [
    "name",
    "description",
    "project_id",
    "state",
    "stage_id",
    "agile_story_points",
    "agile_acceptance_criteria",
    "agile_backlog_sequence",
]
assert env.cr.dbname == DATABASE, "Refuse non-declared lifecycle fixture database"
assert PHASE in (
    "seed_legacy_proxy",
    "check_legacy_proxy",
    "seed_core",
    "check_core",
    "removed_core",
    "seed_bridge",
    "check_bridge",
    "removed_bridge",
    "reinstalled_bridge",
    "reinstalled_core",
), "Unknown disposable phase"


def parameter():
    return env["ir.config_parameter"].sudo()


def native_values(task):
    return record_values(task, NATIVE_FIELDS)


def record_values(record, fields):
    # Preserve native event timestamp precision and normalize relational tuples
    # identically before and after the persisted-data upgrade.
    values = {
        key: value.isoformat() if isinstance(value, (date, datetime)) else value
        for key, value in record.read(fields)[0].items()
    }
    return json.loads(json.dumps(values))


def seed_fixture(bridge):
    from task_concurrency import seed

    manager, project, solution, requirement = seed(
        env, "M8LIFEBRIDGE" if bridge else "M8LIFECORE"
    )
    project.write({"agile_estimation_method": "fibonacci"})
    requirement.write({"audience": "customer"})
    document = (
        env["project.agile.solution.document"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC lifecycle brief",
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
                "title": "SYNTHETIC exact lifecycle scope",
                "requirement_revision_ids": [Command.set(requirement.ids)],
                "section_ids": [
                    Command.create(
                        {
                            "title": "Scope",
                            "body": "<p>SYNTHETIC retained exact scope.</p>",
                        }
                    )
                ],
            }
        )
    )
    baseline.action_submit()
    baseline.action_approve()
    task = (
        env["project.task"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC retained native work",
                "project_id": project.id,
                "agile_item_type_id": env.ref(
                    "project_agile.project_agile_item_type_story"
                ).id,
                "description": "<p>Manual native description.</p>",
                "agile_story_points": 3,
                "agile_acceptance_criteria": "<p>Manual native criteria.</p>",
                "agile_backlog_sequence": 47,
            }
        )
    )
    intent = (
        env["project.agile.solution.task.intent"]
        .with_user(manager)
        .create(
            {
                "solution_id": solution.id,
                "name": task.name,
                "operation": "link",
                "task_id": task.id,
                "document_revision_id": baseline.id,
                "requirement_revision_ids": [Command.set(requirement.ids)],
            }
        )
    )
    assert intent.action_confirm()["res_id"] == task.id
    acceptance = (
        env["project.agile.requirement.acceptance"]
        .with_user(manager)
        .create(
            {
                "document_revision_id": baseline.id,
                "requirement_revision_id": requirement.id,
                "decision": "accepted",
                "authority_label": "SYNTHETIC internal evaluator",
                "criteria_evaluated": requirement.acceptance_expectations,
                "evidence": (
                    "SYNTHETIC disposable lifecycle observation; not customer evidence"
                ),
            }
        )
    )
    data = {
        "manager": manager.id,
        "task": task.id,
        "baseline": baseline.id,
        "intent": intent.id,
        "requirement": requirement.id,
        "acceptance": acceptance.id,
        "snapshot": baseline.snapshot_json,
        "projection": baseline.action_projection("internal"),
        "evidence": acceptance.evidence,
        "acceptance_values": record_values(
            acceptance,
            [
                "requirement_revision_id",
                "document_revision_id",
                "decision",
                "authority_label",
                "criteria_evaluated",
                "evidence",
                "recorded_by_id",
                "recorded_by_label",
                "recorded_at",
                "supersedes_id",
            ],
        ),
    }
    if not PHASE.endswith("legacy_proxy"):
        data.update(seed_portal(manager, project, baseline, requirement))
    if bridge:
        data.update(seed_sprint(env, manager, project, task))
    data["native"] = native_values(task)
    parameter().set_param(KEY, json.dumps(data, sort_keys=True))
    env.cr.commit()


def seed_sprint(env, manager, project, task):
    team = (
        env["project.agile.team"]
        .with_user(manager)
        .create({"name": "SYNTHETIC lifecycle team", "project_id": project.id})
    )
    sprint = (
        env["project.sprint"]
        .with_user(manager)
        .create(
            {
                "name": "SYNTHETIC lifecycle Sprint",
                "team_id": team.id,
                "project_id": project.id,
            }
        )
    )
    task.write({"sprint_id": sprint.id})
    sprint.action_start()
    event = (
        env["project.sprint.scope.event"]
        .with_user(manager)
        .search([("task_id", "=", task.id), ("event_type", "=", "committed")])
    )
    context = (
        env["project.agile.solution.sprint.context"]
        .with_user(manager)
        .search([("scope_event_id", "=", event.id)])
    )
    assert (
        len(event) == len(context) == 1 and event.solution_capture_status == "captured"
    )
    return {
        "sprint": sprint.id,
        "event": event.id,
        "context": context.id,
        "payload": context.payload_json,
        "event_values": record_values(
            event, ["event_type", "story_points", "task_id", "event_at"]
        ),
    }


def check_core(data):
    caller = env["project.agile.solution.revision"].with_user(data["manager"])
    baseline = caller.browse(data["baseline"])
    assert baseline.state == "approved" and baseline.snapshot_json == data["snapshot"]
    assert baseline.action_projection("internal") == data["projection"]
    intent = (
        env["project.agile.solution.task.intent"]
        .with_user(data["manager"])
        .browse(data["intent"])
    )
    assert (
        intent.state == "consumed" and intent.action_confirm()["res_id"] == data["task"]
    )
    acceptance = (
        env["project.agile.requirement.acceptance"]
        .with_user(data["manager"])
        .browse(data["acceptance"])
    )
    assert acceptance.evidence == data["evidence"] and acceptance.decision == "accepted"
    assert acceptance.decision_source == "internal_proxy"
    assert not acceptance.publication_id and not acceptance.portal_partner_id
    assert (
        record_values(acceptance, list(data["acceptance_values"].keys() - {"id"}))
        == data["acceptance_values"]
    )
    if "publication" in data:
        publication = env["project.agile.solution.portal.publication"].browse(
            data["publication"]
        )
        assert (
            publication.with_user(data["client"]).action_view() == data["portal_view"]
        )
        assert (
            record_values(
                publication,
                [
                    "payload_json",
                    "payload_sha256",
                    "snapshot_sha256",
                    "published_by_id",
                    "published_at",
                ],
            )
            == data["publication_values"]
        )
        revoked = env[publication._name].browse(data["revoked_publication"])
        assert revoked.revoked_at.isoformat() == data["revoked_at"]
        assert (
            env["project.agile.requirement.acceptance"]
            .browse(data["portal_acceptance"])
            .decision_source
            == "portal"
        )


def check_event(data):
    event = (
        env["project.sprint.scope.event"]
        .with_user(data["manager"])
        .browse(data["event"])
    )
    assert (
        record_values(event, ["event_type", "story_points", "task_id", "event_at"])
        == data["event_values"]
    )
    sprint = env["project.sprint"].with_user(data["manager"]).browse(data["sprint"])
    assert sprint.state == "active" and sprint.committed_task_ids.ids == [data["task"]]
    return event


def check_phase(data):
    task = env["project.task"].with_user(data["manager"]).browse(data["task"])
    assert task.exists() and native_values(task) == data["native"], (
        "Optional lifecycle changed native work"
    )
    if PHASE == "removed_core":
        assert "project.agile.solution" not in env.registry
        assert "solution_maintenance_reason" not in task._fields
        return
    if PHASE == "reinstalled_core":
        assert not env["project.agile.solution"].search([]), (
            "Uninstall is destructive, not history retention"
        )
        assert not env["project.agile.solution.portal.publication"].search([])
        assert not env["project.agile.solution.portal.document.decision"].search([])
        assert not env["project.agile.requirement.acceptance"].search([])
        assert not env["project.agile.solution.task.intent"].search([]), (
            "Reinstall must not fabricate consumed intents"
        )
        return
    check_core(data)
    if PHASE in ("check_core", "check_legacy_proxy"):
        return
    event = check_event(data)
    if PHASE == "removed_bridge":
        assert "project.agile.solution.sprint.context" not in env.registry
        assert "solution_capture_status" not in event._fields
        return
    contexts = env["project.agile.solution.sprint.context"].with_user(data["manager"])
    if PHASE == "check_bridge":
        assert contexts.browse(data["context"]).payload_json == data["payload"]
        assert event.solution_capture_status == "captured"
        return
    assert event.solution_capture_status == "not_available", (
        "Bridge reinstall fabricated historical proof"
    )
    assert not contexts.search([("scope_event_id", "=", event.id)])
    task.write({"agile_story_points": 5})
    fresh = event.search(
        [("task_id", "=", task.id), ("event_type", "=", "reestimated")]
    )
    assert len(fresh) == 1 and fresh.solution_capture_status == "captured"
    assert (
        contexts.search([("scope_event_id", "=", fresh.id)]).requirement_revision_id.id
        == data["requirement"]
    )
    assert event.solution_capture_status == "not_available"
    env.cr.commit()


def seed_portal(manager, project, baseline, requirement):
    from odoo.addons.mail.tests.common import mail_new_test_user

    client = mail_new_test_user(
        env, "solution_lifecycle_client_" + PHASE, groups="base.group_portal"
    )
    project.write({"privacy_visibility": "portal"})
    project.message_subscribe(partner_ids=client.partner_id.ids)
    baseline.document_id.write({"portal_approver_id": client.id})
    publication = env["project.agile.solution.portal.publication"].browse(
        baseline.action_issue_portal(client.id)
    )
    publication.with_user(client).action_decide_document(
        "approved", comment="Exact lifecycle disclosure"
    )
    event = publication.with_user(client).action_decide_requirement(
        requirement.requirement_id.key,
        requirement.number,
        "accepted",
        "Lifecycle criteria",
        "Lifecycle observation",
    )
    view = publication.with_user(client).action_view()
    viewer = mail_new_test_user(
        env, "solution_lifecycle_viewer_" + PHASE, groups="base.group_portal"
    )
    project.message_subscribe(partner_ids=viewer.partner_id.ids)
    revoked = env[publication._name].browse(baseline.action_issue_portal(viewer.id))
    revoked.with_user(manager).action_revoke()
    return {
        "client": client.id,
        "publication": publication.id,
        "portal_view": view,
        "publication_values": record_values(
            publication,
            [
                "payload_json",
                "payload_sha256",
                "snapshot_sha256",
                "published_by_id",
                "published_at",
            ],
        ),
        "portal_acceptance": event["id"],
        "revoked_publication": revoked.id,
        "revoked_at": revoked.revoked_at.isoformat(),
    }


if PHASE.startswith("seed_"):
    seed_fixture(PHASE == "seed_bridge")
else:
    check_phase(json.loads(parameter().get_param(KEY)))
# Stdout is the phase consumer's canonical result ABI.
print("M8_PERSISTED_LIFECYCLE_OK " + PHASE, flush=True)  # pylint: disable=print-used

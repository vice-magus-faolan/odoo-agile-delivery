"""Canonical disposable multi-process apply/disable/manual/crash regressions.

Run as stdin to `odoo shell`, only on the declared disposable verification DB.
Worker cursors/processes are independent; no TransactionCase commit or live data.
"""

import json
import os
import subprocess
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from odoo import Command, fields

from odoo.addons.mail.tests.common import mail_new_test_user

assert env.cr.dbname in {"odoo_agile_verify_install", "m7_apply"}
assert not env["project.git.policy.effect"].search([]), (
    "Probe requires an empty disposable policy fixture"
)
capability = "project_agile_git_automation.group_git_policy_manager"
author = mail_new_test_user(env, "race_policy_author", groups=capability)
approver = mail_new_test_user(env, "race_policy_approver", groups=capability)
executor = mail_new_test_user(
    env, "race_policy_executor", groups="project.group_project_user"
)
worker_source = Path("/mnt/policy-tests/git_policy_concurrency_worker.py").read_text()
command = [
    "odoo",
    "shell",
    "--config=/etc/odoo/odoo.conf",
    "--database",
    env.cr.dbname,
    "--no-http",
]
results = []
fixture_index = 0


def fixture(discover=True, dependency_kind=None):
    global fixture_index
    fixture_index += 1
    executor.active = True
    project = env["project.project"].create(
        {
            "name": "Policy race",
            "company_id": env.company.id,
            "privacy_visibility": "employees",
            "agile_enabled": True,
            "agile_key": "RACE" + str(fixture_index),
        }
    )
    repository = env["project.git.repository"].create(
        {
            "name": "Synthetic race",
            "project_id": project.id,
            "provider": "github",
            "provider_repository_id": "race-" + str(fixture_index),
            "canonical_url": "https://github.com/synthetic/race",
        }
    )
    stages = env["project.task.type"].create(
        [
            {"name": n, "project_ids": [Command.link(project.id)]}
            for n in ("Source", "QA", "Manual")
        ]
    )
    task = env["project.task"].create(
        {
            "name": "Synthetic race task",
            "project_id": project.id,
            "stage_id": stages[0].id,
        }
    )
    blocker = env["project.task"]
    if dependency_kind:
        project.write({"allow_task_dependencies": True})
        blocker = env["project.task"].create(
            {
                "name": "Synthetic dependency blocker",
                "project_id": project.id,
                "stage_id": stages[0].id,
                "state": "1_done"
                if dependency_kind == "blocker_state"
                else "01_in_progress",
            }
        )
        if dependency_kind == "blocker_state":
            task.with_user(executor).write(
                {"depend_on_ids": [Command.link(blocker.id)]}
            )
        env.flush_all()
    rule = (
        env["project.git.policy.rule"]
        .with_user(author)
        .create({"name": "Race rule", "repository_id": repository.id})
    )
    revision = (
        env["project.git.policy.revision"]
        .with_user(author)
        .create(
            {
                "rule_id": rule.id,
                "target_branch": "main",
                "allowed_source_stage_ids": [Command.set(stages[:1].ids)],
                "target_stage_id": stages[1].id,
                "execution_user_id": executor.id,
            }
        )
    )
    project.with_user(author).action_enable_git_policy(mode="apply")
    now = fields.Datetime.now()
    with patch.object(fields.Datetime, "now", return_value=now - timedelta(hours=1)):
        revision.with_user(approver).action_activate(
            acknowledge_native_side_effects=True
        )
    delivery = env["project.git.delivery"].create(
        {
            "repository_id": repository.id,
            "provider_delivery_id": "race-pr",
            "event_type": "pull_request",
            "payload_sha256": "b" * 64,
            "payload_size": 300,
            "state": "processed",
            "attempt_count": 1,
            "received_at": now - timedelta(minutes=10),
            "processed_at": now - timedelta(minutes=5),
        }
    )
    pr = env["project.git.pull.request"].create(
        {
            "repository_id": repository.id,
            "provider_request_id": "race-pr",
            "state": "merged",
            "target_branch": "main",
            "head_sha": "a" * 40,
            "merged_at": now - timedelta(minutes=15),
            "updated_at": now - timedelta(minutes=15),
            "ordering_state": "known",
            "provenance_delivery_id": delivery.id,
        }
    )
    env["project.git.task.association"].create(
        {
            "repository_id": repository.id,
            "task_id": task.id,
            "source_type": "pull_request",
            "source_provider_id": pr.provider_request_id,
        }
    )
    env["project.git.association.audit"].create(
        {
            "repository_id": repository.id,
            "task_id": task.id,
            "delivery_id": delivery.id,
            "source_type": "pull_request",
            "source_provider_id": pr.provider_request_id,
            "source_field": "title",
            "agile_key": task.agile_key,
            "outcome": "associated",
            "reason": "exact_key",
        }
    )
    if discover:
        attempts, _, _ = (
            env["project.git.policy.attempt"]
            .with_user(author)
            ._discover_repository(repository.with_user(author), 0)
        )
        assert len(attempts) == 1
    else:
        attempts = env["project.git.policy.attempt"]
    env.cr.commit()
    return {
        "project_id": project.id,
        "repository_id": repository.id,
        "task_id": task.id,
        "pr_id": pr.id,
        "revision_id": revision.id,
        "attempt_id": attempts.id if attempts else False,
        "source_stage_id": stages[0].id,
        "target_stage_id": stages[1].id,
        "other_stage_id": stages[2].id,
        "author_id": author.id,
        "executor_id": executor.id,
        "blocker_id": blocker.id if blocker else False,
    }


def refresh():
    env.cr.rollback()
    env.invalidate_all()


def wait(directory, filename):
    deadline = time.monotonic() + 15
    while not (directory / filename).exists():
        if time.monotonic() > deadline:
            raise RuntimeError("Independent process rendezvous missing: " + filename)
        time.sleep(0.02)


def launch(directory, data, name, operation):
    values = {
        **data,
        "directory": str(directory),
        "worker": name,
        "operation": operation,
    }
    child_env = {**os.environ, "GIT_POLICY_SCENARIO": json.dumps(values)}
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=child_env,
    )
    process.stdin.write(worker_source)
    process.stdin.close()
    process.stdin = None
    return process


def finish(directory, name, process, expected=0):
    stdout, stderr = process.communicate(timeout=25)
    if process.returncode != expected:
        raise RuntimeError(
            f"Fixture worker {name} exited {process.returncode}: {stdout}\n{stderr}"
        )
    return (
        json.loads((directory / (name + ".json")).read_text())
        if expected == 0
        else {"exit": expected}
    )


def state(data):
    refresh()
    task = env["project.task"].browse(data["task_id"])
    attempts = env["project.git.policy.attempt"].search(
        [("repository_id", "=", data["repository_id"])]
    )
    effects = env["project.git.policy.effect"].search(
        [("repository_id", "=", data["repository_id"])]
    )
    return task, attempts, effects


def lease(data):
    item = env["project.git.policy.attempt"]._claim_attempt()
    assert item.id == data["attempt_id"]
    token = item.lease_token
    env.cr.commit()
    return {**data, "lease_token": token}


def recover(data):
    refresh()
    attempt = env["project.git.policy.attempt"].browse(data["attempt_id"])
    if attempt.state == "processing":
        attempt._set_schedule(
            {"lease_expires_at": fields.Datetime.now() - timedelta(seconds=1)}
        )
    env.cr.commit()
    claimed = env["project.git.policy.attempt"]._claim_attempt()
    assert claimed == attempt
    claimed._process_claim()
    env.cr.commit()
    return state(data)


# Exercise the actual native ir.cron separate-cursor/progress contract,
# not a mocked commit.
data = fixture(discover=False)
env.ref("project_agile_git_automation.ir_cron_git_policy").method_direct_trigger()
task, attempts, effects = state(data)
assert len(effects) == 1 and task.stage_id.id == data["target_stage_id"]
assert effects.execution_user_id == executor and task.write_uid == executor
assert attempts.state == "applied"
results.append(
    {
        "scenario": "native_cron",
        "effect_count": len(effects),
        "actor_is_nonadmin": effects.execution_user_id.id != 1,
    }
)

# Native progress still performs the real commit; only its remaining time is
# exhausted. Separate native cursors prove discovery and settled-item recovery.
data = fixture(discover=False)
cron = env.ref("project_agile_git_automation.ir_cron_git_policy")
cron_class = type(cron)
commit_progress = cron_class._commit_progress


def exhaust_budget(self, *args, **kwargs):
    commit_progress(self, *args, **kwargs)
    return 0


with patch.object(cron_class, "_commit_progress", exhaust_budget):
    cron.method_direct_trigger()
task, attempts, effects = state(data)
assert len(attempts) == 1 and attempts.state == "queued" and not effects
assert task.stage_id.id == data["source_stage_id"]
results.append(
    {
        "scenario": "native_budget_after_discovery",
        "queued": len(attempts),
        "effects": len(effects),
    }
)
with patch.object(cron_class, "_commit_progress", exhaust_budget):
    cron.method_direct_trigger()
task, attempts, effects = state(data)
assert attempts.state == "applied" and len(effects) == 1
cron.method_direct_trigger()
task, attempts, effects = state(data)
assert len(effects) == 1 and attempts.attempt_count == 1
results.append(
    {
        "scenario": "native_budget_after_settlement_recovery",
        "claims": attempts.attempt_count,
        "effects": len(effects),
    }
)

with tempfile.TemporaryDirectory(
    prefix="git-policy-races-", dir="/var/lib/odoo"
) as temporary:
    workdir = Path(temporary)
    data = fixture()
    directory = workdir / "claims"
    directory.mkdir()
    processes = [launch(directory, data, name, "claim") for name in ("a", "b")]
    try:
        for name in ("a", "b"):
            wait(directory, name + ".ready")
        (directory / "start").write_text("start")
        rows = [
            finish(directory, name, process)
            for name, process in zip(("a", "b"), processes, strict=False)
        ]
        assert (
            len({r["pid"] for r in rows}) == 2
            and len({r["backend_pid"] for r in rows}) == 2
        )
        assert sum(r["claimed"] for r in rows) == 1, rows
        task, attempts, effects = state(data)
        assert attempts.state == "applied" and len(effects) == 1
        results.append(
            {
                "scenario": "two_concurrent_claims",
                "workers": rows,
                "effects": len(effects),
            }
        )
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()

    for operation in (
        "disable",
        "revoke",
        "revision",
        "manual",
        "identity",
        "fact",
        "stage",
        "manual_dependency",
        "blocker_state",
    ):
        data = lease(
            fixture(
                dependency_kind=operation
                if operation in {"manual_dependency", "blocker_state"}
                else None
            )
        )
        directory = workdir / operation
        directory.mkdir()
        writer = launch(directory, data, "writer", operation)
        worker = None
        try:
            wait(directory, "writer.ready")
            worker = launch(directory, data, "applier", "process")
            wait(directory, "applier.executing")
            time.sleep(0.2)
            (directory / "writer.release").write_text("release")
            rows = [
                finish(directory, "writer", writer),
                finish(directory, "applier", worker),
            ]
            assert (
                len({r["pid"] for r in rows}) == 2
                and len({r["backend_pid"] for r in rows}) == 2
            )
            task, attempts, effects = state(data)
            assert not effects and task.stage_id.id == data["source_stage_id"], (
                operation,
                attempts.state,
                attempts.reason,
            )
            assert attempts.state in {"revoked", "rejected"}, (
                operation,
                attempts.state,
            )
            if operation in {"manual_dependency", "blocker_state"}:
                assert (attempts.state, attempts.reason) == ("rejected", "stale_task")
                assert task.state == "01_in_progress"
                assert (
                    task.git_policy_transition_version
                    > attempts.expected_transition_version
                )
            assert rows[1]["restarts"] >= 1, rows
            results.append(
                {
                    "scenario": operation + "_wins_execution_race",
                    "workers": rows,
                    "state": attempts.state,
                    "reason": attempts.reason,
                }
            )
        finally:
            for process in (writer, worker):
                if process and process.poll() is None:
                    process.kill()
                    process.communicate()

    data = lease(fixture())
    directory = workdir / "apply_first"
    directory.mkdir()
    applier = launch(directory, data, "applier", "apply_hold")
    writer = None
    try:
        wait(directory, "applier.ready")
        writer = launch(directory, data, "writer", "disable")
        wait(directory, "writer.started")
        time.sleep(0.2)
        (directory / "applier.release").write_text("release")
        wait(directory, "writer.ready")
        (directory / "writer.release").write_text("release")
        rows = [
            finish(directory, "applier", applier),
            finish(directory, "writer", writer),
        ]
        task, attempts, effects = state(data)
        assert len(effects) == 1 and attempts.state == "applied"
        assert not env["project.project"].browse(data["project_id"]).git_policy_enabled
        attempts._process_claim(data["lease_token"])
        assert len(effects) == 1 and task.stage_id.id == data["target_stage_id"]
        results.append(
            {
                "scenario": "settled_effect_precedes_disable",
                "workers": rows,
                "effects": len(effects),
            }
        )
    finally:
        for process in (applier, writer):
            if process and process.poll() is None:
                process.kill()
                process.communicate()

    for operation, exit_code in (("claim_crash", 79), ("write_crash", 77)):
        data = fixture()
        directory = workdir / operation
        directory.mkdir()
        process = launch(directory, data, "crasher", operation)
        try:
            wait(directory, "crasher.ready")
            (directory / "start").write_text("start")
            finish(directory, "crasher", process, expected=exit_code)
            task, attempts, effects = state(data)
            assert (
                not effects
                and attempts.state == "queued"
                and task.stage_id.id == data["source_stage_id"]
            )
            assert (
                task.git_policy_transition_version
                == attempts.expected_transition_version
            )
            task, attempts, effects = recover(data)
            assert len(effects) == 1 and attempts.state == "applied"
            results.append(
                {
                    "scenario": operation,
                    "exit_code": exit_code,
                    "atomic_rollback": True,
                    "recovery_effects": len(effects),
                }
            )
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

# Stdout is this disposable probe's machine-readable result ABI.
print(  # pylint: disable=print-used
    "GIT_POLICY_CONCURRENCY=" + json.dumps(results, sort_keys=True)
)

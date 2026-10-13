"""Signed provider lifecycle coverage without a required GitHub dependency."""

import hashlib
import hmac
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestGitPolicyGitHubLifecycle(TransactionCase):
    """Use actual signed ingress/normalization before nonadmin policy execution."""

    def setUp(self):
        super().setUp()
        if "_claim_github_delivery" not in dir(self.env["project.git.delivery"]):
            self.skipTest("Optional GitHub adapter is not installed.")
        capability = "project_agile_git_automation.group_git_policy_manager"
        self.author = mail_new_test_user(
            self.env, "lifecycle_author", groups=capability
        )
        self.approver = mail_new_test_user(
            self.env, "lifecycle_approver", groups=capability
        )
        self.executor = mail_new_test_user(
            self.env, "lifecycle_executor", groups="project.group_project_user"
        )
        self.project = self.env["project.project"].create(
            {
                "name": "Signed lifecycle",
                "company_id": self.env.company.id,
                "agile_enabled": True,
                "agile_key": "LFC",
                "privacy_visibility": "employees",
            }
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "Synthetic lifecycle",
                "project_id": self.project.id,
                "provider": "github",
                "provider_repository_id": "lifecycle",
                "canonical_url": "https://github.com/synthetic/lifecycle",
                "webhook_secret": "synthetic-lifecycle-secret",
                "retention_policy": "redacted_excerpt",
            }
        )
        self.stages = self.env["project.task.type"].create(
            [
                {"name": name, "project_ids": [Command.link(self.project.id)]}
                for name in ("Source", "QA")
            ]
        )
        self.task = self.env["project.task"].create(
            {
                "name": "Lifecycle task",
                "project_id": self.project.id,
                "stage_id": self.stages[0].id,
            }
        )
        self.rule = (
            self.env["project.git.policy.rule"]
            .with_user(self.author)
            .create(
                {
                    "name": "Explicit stage transition",
                    "repository_id": self.repository.id,
                }
            )
        )
        self.revision = (
            self.env["project.git.policy.revision"]
            .with_user(self.author)
            .create(
                {
                    "rule_id": self.rule.id,
                    "target_branch": "main",
                    "allowed_source_stage_ids": [Command.set(self.stages[:1].ids)],
                    "target_stage_id": self.stages[1].id,
                    "execution_user_id": self.executor.id,
                }
            )
        )
        self.now = fields.Datetime.now()
        self.project.with_user(self.author).action_enable_git_policy(mode="apply")
        with patch.object(
            fields.Datetime, "now", return_value=self.now - timedelta(hours=1)
        ):
            self.revision.with_user(self.approver).action_activate(
                acknowledge_native_side_effects=True
            )

    def _signed_delivery(self, identity, minutes, *, merged=True, title=None):
        # Import only after proving the optional adapter is installed. No manifest
        # dependency, forged processed receipt or manually authored association.
        from odoo.addons.project_agile_git_github.controllers import github_webhook

        stamp = (self.now - timedelta(minutes=minutes)).isoformat() + "Z"
        payload = {
            "repository": {"id": self.repository.provider_repository_id},
            "number": 11,
            "pull_request": {
                "id": 11,
                "state": "closed" if merged else "open",
                "merged": merged,
                "merged_at": stamp if merged else None,
                "updated_at": stamp,
                "title": self.task.agile_key if title is None else title,
                "body": "",
                "head": {"ref": "feature/no-key", "sha": "a" * 40},
                "base": {"ref": "main"},
            },
        }
        raw = json.dumps(payload, separators=(",", ":")).encode()
        signature = (
            "sha256="
            + hmac.new(b"synthetic-lifecycle-secret", raw, hashlib.sha256).hexdigest()
        )
        request = Request(
            EnvironBuilder(
                path="/project_agile_git_github/webhook",
                method="POST",
                data=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": identity,
                    "X-Hub-Signature-256": signature,
                },
            ).get_environ()
        )
        self.env.flush_all()
        public = self.env(user=self.env.ref("base.public_user").id)
        with patch.object(
            github_webhook, "request", SimpleNamespace(env=public, httprequest=request)
        ):
            self.assertEqual(
                github_webhook.GitHubWebhookController().github_webhook().status_code,
                202,
            )
        delivery = self.env["project.git.delivery"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("provider_delivery_id", "=", identity),
            ]
        )
        claim = self.env["project.git.delivery"]._claim_github_delivery()
        self.assertEqual(claim, delivery)
        claim._settle_github_delivery()
        self.assertEqual(delivery.state, "processed", delivery.error_summary)
        return delivery

    def _audits(self, delivery):
        return self.env["project.git.association.audit"].search(
            [("delivery_id", "=", delivery.id)]
        )

    def _discover(self):
        return (
            self.env["project.git.policy.attempt"]
            .with_user(self.author)
            ._discover_repository(
                self.repository.with_user(self.author),
                0,
            )[0]
        )

    def _effects(self):
        return self.env["project.git.policy.effect"].search(
            [("repository_id", "=", self.repository.id)]
        )

    def _apply(self, attempt):
        claim = self.env["project.git.policy.attempt"]._claim_attempt()
        self.assertEqual(claim, attempt)
        claim._process_claim()
        self.assertEqual(attempt.state, "applied", attempt.reason)
        self.assertEqual(self.task.stage_id, self.stages[1])
        self.assertEqual(self.task.write_uid, self.executor)
        self.assertFalse(self.task.is_closed)
        self.assertEqual(len(self._effects()), 1)

    def test_signed_opened_merge_and_repeated_update_keep_current_task_proof(self):
        before = self.task.read(["stage_id", "state", "agile_story_points"])
        opened = self._signed_delivery("opened", 30, merged=False)
        merged = self._signed_delivery("merged", 20)
        updated = self._signed_delivery("updated", 10)
        self.assertEqual(
            before, self.task.read(["stage_id", "state", "agile_story_points"])
        )
        self.assertEqual(self._audits(opened).outcome, "associated")
        for delivery in (merged, updated):
            audit = self._audits(delivery)
            self.assertEqual(
                (audit.outcome, audit.reason), ("already_associated", "duplicate")
            )
            self.assertEqual(audit.task_id, self.task)
        pr = self.env["project.git.pull.request"].search(
            [("repository_id", "=", self.repository.id)]
        )
        self.assertEqual(pr.provenance_delivery_id, updated)
        self._apply(self._discover())
        self._signed_delivery("after-effect", 5)
        self.assertFalse(self._discover())
        self.assertEqual(len(self._effects()), 1)
        self.assertEqual(self._audits(opened).task_id, self.task)

    def test_signed_fresh_merge_is_a_positive_control(self):
        delivery = self._signed_delivery("fresh", 20)
        self.assertEqual(self._audits(delivery).task_id, self.task)
        self._apply(self._discover())

    def test_changed_current_key_cannot_reuse_old_task_proof(self):
        opened = self._signed_delivery("opened", 30, merged=False)
        merged = self._signed_delivery("changed-key", 20, title="LFC-999")
        self.assertEqual(self._audits(opened).task_id, self.task)
        self.assertFalse(self._audits(merged).task_id)
        self.assertEqual(self._audits(merged).reason, "unknown_key")
        self.assertFalse(self._discover())
        self.repository.with_user(self.author).action_dry_run_git_policy()
        decision = self.env["project.git.policy.evaluation"].search(
            [
                ("repository_id", "=", self.repository.id),
            ],
            order="id desc",
            limit=1,
        )
        self.assertEqual(decision.reason, "invalid_provenance")
        self.assertFalse(self._effects())
        self.assertEqual(self.task.stage_id, self.stages[0])

    def test_foreign_and_unknown_keys_have_identical_taskless_diagnostics(self):
        company = self.env["res.company"].create({"name": "Foreign lifecycle company"})
        project = (
            self.env["project.project"]
            .with_company(company)
            .create(
                {
                    "name": "Foreign lifecycle",
                    "company_id": company.id,
                    "agile_enabled": True,
                    "agile_key": "FRN",
                    "privacy_visibility": "employees",
                }
            )
        )
        foreign = (
            self.env["project.task"]
            .with_company(company)
            .create({"name": "Foreign", "project_id": project.id})
        )
        delivery = self._signed_delivery(
            "foreign", 20, title=foreign.agile_key + " FRN-999"
        )
        audits = self._audits(delivery)
        self.assertEqual(len(audits), 2)
        self.assertEqual(set(audits.mapped("reason")), {"unknown_key"})
        self.assertFalse(audits.task_id)
        self.assertFalse(self._discover())
        self.assertFalse(self._effects())

    def test_archived_duplicate_does_not_gain_current_task_proof(self):
        opened = self._signed_delivery("opened", 30, merged=False)
        self.task.with_user(self.author).write({"active": False})
        delivery = self._signed_delivery("archived", 20)
        self.assertEqual(self._audits(opened).task_id, self.task)
        self.assertEqual(self._audits(delivery).reason, "archived_task")
        self.assertFalse(self._audits(delivery).task_id)
        self.assertFalse(self._discover())
        self.assertFalse(self._effects())

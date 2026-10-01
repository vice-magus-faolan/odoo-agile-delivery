"""Native form tours against real server approval, preview, disable and retry APIs."""
from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestGitPolicyOperationsTour(HttpCase):
    def setUp(self):
        super().setUp()
        capability = "project_agile_git_automation.group_git_policy_manager"
        self.author = mail_new_test_user(self.env, "ops_tour_author", groups=capability)
        self.approver = mail_new_test_user(self.env, "ops_tour_approver", groups=capability)
        self.executor = mail_new_test_user(self.env, "ops_tour_executor", groups="project.group_project_user")
        self.project = self.env["project.project"].create({
            "name": "Policy tour", "company_id": self.env.company.id, "agile_enabled": True,
            "agile_key": "TOUR", "privacy_visibility": "employees",
        })
        self.repository = self.env["project.git.repository"].create({
            "name": "Policy tour", "provider": "github", "provider_repository_id": "policy-tour",
            "canonical_url": "https://github.com/synthetic/policy-tour", "project_id": self.project.id,
        })
        self.stages = self.env["project.task.type"].create([
            {"name": name, "project_ids": [Command.link(self.project.id)]} for name in ("Source", "QA")
        ])
        self.task = self.env["project.task"].create({
            "name": "Tour task", "project_id": self.project.id, "stage_id": self.stages[0].id,
        })
        self.rule = self.env["project.git.policy.rule"].with_user(self.author).create({
            "name": '<img src=x onerror="window.policyInjected=true">', "repository_id": self.repository.id,
        })
        self.revision = self.env["project.git.policy.revision"].with_user(self.author).create({
            "rule_id": self.rule.id, "target_branch": "main", "execution_user_id": self.executor.id,
            "allowed_source_stage_ids": [Command.set(self.stages[:1].ids)], "target_stage_id": self.stages[1].id,
        })
        now = fields.Datetime.now()
        delivery = self.env["project.git.delivery"].create({
            "repository_id": self.repository.id, "provider_delivery_id": "tour-pr", "event_type": "pull_request",
            "payload_sha256": "b" * 64, "payload_size": 300, "state": "processed", "attempt_count": 1,
            "received_at": now - timedelta(minutes=10), "processed_at": now - timedelta(minutes=5),
        })
        pr = self.env["project.git.pull.request"].create({
            "repository_id": self.repository.id, "provider_request_id": "tour-pr", "state": "merged",
            "target_branch": "main", "head_sha": "a" * 40, "merged_at": now - timedelta(minutes=15),
            "updated_at": now - timedelta(minutes=15), "ordering_state": "known", "provenance_delivery_id": delivery.id,
        })
        self.env["project.git.task.association"].create({"repository_id": self.repository.id, "task_id": self.task.id,
            "source_type": "pull_request", "source_provider_id": pr.provider_request_id})
        self.env["project.git.association.audit"].create({
            "repository_id": self.repository.id, "task_id": self.task.id, "delivery_id": delivery.id,
            "source_type": "pull_request", "source_provider_id": pr.provider_request_id,
            "source_field": "title", "agile_key": self.task.agile_key, "outcome": "associated", "reason": "exact_key",
        })

    def _url(self, action, record):
        return f"/odoo/action-{self.env.ref('project_agile_git_automation.' + action).id}/{record.id}"

    def test_native_approval_preview_and_disabled_form_journey(self):
        self.project.with_user(self.author).action_enable_git_policy()
        self.start_tour(self._url("action_git_policy_revisions", self.revision),
                        "git_policy_approve", login=self.approver.login)
        self.env.invalidate_all()
        self.assertEqual(self.revision.approver_id, self.approver)
        self.assertTrue(self.revision.approved_at)
        self.assertEqual(self.rule.policy_status, "dry_run")
        self.start_tour(self._url("action_git_policy_rules", self.rule),
                        "git_policy_preview", login=self.author.login)
        self.env.invalidate_all()
        decision = self.env["project.git.policy.evaluation"].search([("rule_id", "=", self.rule.id)])
        self.assertEqual((decision.outcome, decision.reason), ("rejected", "before_cutoff"))
        self.assertEqual(self.task.stage_id, self.stages[0])
        self.assertFalse(self.env["project.git.policy.effect"].search([]))
        self.start_tour(self._url("action_git_policy_rules", self.rule),
                        "git_policy_disable", login=self.author.login)
        self.env.invalidate_all()
        self.assertEqual(self.rule.policy_status, "disabled")
        self.assertFalse(self.rule.activation_id)

    def test_native_retry_confirmation_preserves_original_attempt(self):
        self.project.with_user(self.author).action_enable_git_policy(mode="apply")
        with patch.object(fields.Datetime, "now", return_value=fields.Datetime.now() - timedelta(hours=1)):
            self.revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)
        attempts = self.env["project.git.policy.attempt"]
        attempt = attempts.with_user(self.author)._discover_repository(self.repository.with_user(self.author), 0)[0]
        self.assertEqual(len(attempt), 1)
        claim = attempts._claim_attempt()
        with patch.object(type(self.env["project.git.policy.effect"]), "_append", side_effect=RuntimeError("synthetic tour")):
            claim._process_claim()
        self.assertEqual(attempt.state, "retryable")
        before = attempt.read(["activation_id", "observation_id", "task_id", "expected_transition_version", "attempt_count"])
        self.start_tour(self._url("action_git_policy_attempts", attempt), "git_policy_retry", login=self.author.login)
        self.env.invalidate_all()
        self.assertEqual(attempt.state, "queued")
        self.assertEqual(before, attempt.read(["activation_id", "observation_id", "task_id", "expected_transition_version", "attempt_count"]))
        self.assertEqual(attempt.event_ids.filtered(lambda row: row.reason == "operator_retry").actor_id, self.author)
        self.assertEqual(self.task.stage_id, self.stages[0])
        self.assertFalse(self.env["project.git.policy.effect"].search([]))

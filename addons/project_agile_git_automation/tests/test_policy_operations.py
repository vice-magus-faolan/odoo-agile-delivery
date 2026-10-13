"""Operator recovery never replaces the immutable candidate or native authority."""

import logging
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .test_policy_apply import TestGitPolicyApply

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestGitPolicyOperations(TestGitPolicyApply):
    """Reuse the trusted non-admin fixture and retain all inherited apply checks."""

    def _transient_attempt(self):
        attempt = self._discover()
        with patch.object(
            type(self.effects), "_append", side_effect=RuntimeError("synthetic failure")
        ):
            self._apply()
        self.assertEqual(
            (attempt.state, attempt.reason), ("retryable", "transient_failure")
        )
        return attempt

    def test_operator_retry_keeps_candidate_and_budget_and_records_actor(self):
        attempt = self._transient_attempt()
        fixed = [
            "task_id",
            "agile_key",
            "activation_id",
            "revision_id",
            "observation_id",
            "provider_request_id",
            "expected_stage_id",
            "expected_transition_version",
            "attempt_count",
        ]
        before = attempt.read(fixed)
        fence = self.task.git_policy_transition_version
        self.assertTrue(
            attempt.with_user(self.author)
            .with_context(task_id=999, policy_trusted=True)
            .action_retry()
        )
        self.assertEqual(attempt.state, "queued")
        self.assertEqual(before, attempt.read(fixed))
        self.assertEqual(self.task.git_policy_transition_version, fence)
        event = attempt.event_ids.filtered(lambda row: row.reason == "operator_retry")
        self.assertEqual(event.actor_id, self.author)
        self.assertEqual(self._apply(), attempt)
        self.assertEqual(attempt.state, "applied")
        self.assertEqual(self.effects.search_count([]), 1)
        with self.assertRaises(ValidationError):
            attempt.with_user(self.author).action_retry()

    def test_retry_rejects_public_identity_and_argument_widening(self):
        attempt = self._transient_attempt()
        for user in (self.executor, self.env.user):
            with self.assertRaises(AccessError):
                attempt.with_user(user).action_retry()
        with self.assertRaises(TypeError):
            attempt.with_user(self.author).action_retry(task_id=self.task.id)
        self.assertEqual(attempt.state, "retryable")

    def test_retry_rejects_stale_task_without_refreshing_fence(self):
        attempt = self._transient_attempt()
        old = attempt.expected_transition_version
        self.task.with_user(self.executor).write({"stage_id": self.stages[2].id})
        self.task.with_user(self.executor).write({"stage_id": self.stages[0].id})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            attempt.with_user(self.author).action_retry()
        self.assertEqual(attempt.expected_transition_version, old)
        self.assertEqual(attempt.state, "retryable")
        self.assertFalse(self.effects.search([]))

    def test_retry_rejects_disabled_revoked_expired_changed_and_consumed(self):
        attempt = self._transient_attempt()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.project.with_user(self.author).action_disable_git_policy()
            attempt.with_user(self.author).action_retry()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.executor.active = False
            attempt.with_user(self.author).action_retry()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.pr.write({"head_sha": "c" * 40})
            attempt.with_user(self.author).action_retry()
        with patch.object(
            fields.Datetime, "now", return_value=self.now + timedelta(days=2)
        ):
            with self.assertRaises(ValidationError), self.env.cr.savepoint():
                attempt.with_user(self.author).action_retry()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            attempt._set_schedule({"attempt_count": 5})
            attempt.with_user(self.author).action_retry()
        self.now += timedelta(minutes=2)
        self._apply()
        self.assertEqual(attempt.state, "applied")
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            attempt._set_schedule({"state": "retryable", "reason": "transient_failure"})
            attempt.with_user(self.author).action_retry()
        self.assertEqual(self.effects.search_count([]), 1)

    def test_retry_obeys_live_task_company_search_group_export_and_read(self):
        attempt = self._transient_attempt()
        hidden = self.env["ir.rule"].create(
            {
                "name": "Hide operator task",
                "model_id": self.env["ir.model"]._get("project.task").id,
                "domain_force": "[('name', '=', 'not visible')]",
            }
        )
        reader = attempt.with_user(self.author)
        self.assertEqual(reader.search_count([("id", "=", attempt.id)]), 0)
        self.assertFalse(
            reader._read_group([("id", "=", attempt.id)], ["state"], ["__count"])
        )
        for operation in (
            lambda: reader.action_retry(),
            lambda: reader.read(["agile_key"]),
            lambda: reader.export_data(["agile_key"]),
        ):
            with self.assertRaises(AccessError):
                operation()
        hidden.unlink()
        other = self.env["res.company"].create({"name": "Operator other company"})
        with self.assertRaises(AccessError):
            reader.with_context(allowed_company_ids=other.ids).action_retry()
        self.assertEqual(attempt.state, "retryable")

    def test_retry_cannot_revive_terminal_or_claimed_or_queued_attempt(self):
        attempt = self._discover()
        for state in (
            "queued",
            "waiting",
            "processing",
            "failed",
            "rejected",
            "no_op",
            "revoked",
            "expired",
        ):
            with self.env.cr.savepoint():
                attempt._set_schedule({"state": state, "reason": "transient_failure"})
                with self.assertRaises(ValidationError):
                    attempt.with_user(self.author).action_retry()
        self.assertFalse(self.effects.search([]))

    def test_native_rule_status_and_fixed_project_navigation(self):
        self.assertEqual(self.rule.with_user(self.author).policy_status, "active")
        result = self.project.with_user(self.author).action_open_git_policy_attempts()
        self.assertEqual(result["res_model"], "project.git.policy.attempt")
        self.assertEqual(result["domain"], [("project_id", "=", self.project.id)])
        self.rule.with_user(self.author).action_disable()
        self.assertEqual(self.rule.with_user(self.author).policy_status, "disabled")
        self.project.with_user(self.author).action_disable_git_policy()
        self.project.with_user(self.author).action_enable_git_policy()
        self._successor()
        self.assertEqual(self.rule.with_user(self.author).policy_status, "dry_run")

    def test_preview_load_is_bounded_with_one_thousand_repository_prs(self):
        values = [
            {
                "repository_id": self.repository.id,
                "provider_request_id": "scale-" + str(i),
                "state": "merged",
                "target_branch": "main",
                "head_sha": "a" * 40,
                "merged_at": self.merged,
                "updated_at": self.merged,
                "ordering_state": "known",
                "provenance_delivery_id": self.delivery.id,
            }
            for i in range(1000)
        ]
        self.env["project.git.pull.request"].create(values)
        self.env.flush_all()
        evaluator = self.env["project.git.policy.evaluation"].with_user(self.author)
        self.env.invalidate_all()
        start = self.env.cr.sql_log_count
        batch = evaluator._load_batch(self.repository.with_user(self.author), 0)
        queries = self.env.cr.sql_log_count - start
        self.assertEqual(len(batch[0]), 20)
        self.assertLessEqual(len(batch[2]), 401)
        self.assertLessEqual(len(batch[3]), 8001)
        self.assertLessEqual(len(batch[4]), 401)
        self.assertLessEqual(queries, 60)
        _logger.info(
            "POLICY_SCALE rows=1001 page=%s load_queries=%s", len(batch[0]), queries
        )

    def test_rule_preview_and_apply_selection_reject_forged_parameters(self):
        with self.assertRaises(AccessError):
            self.rule.with_user(self.executor).action_preview()
        for mode in (True, [], {}, None, "active", " apply"):
            with self.assertRaises(ValidationError):
                self.project.with_user(self.author).action_enable_git_policy(mode=mode)
        with self.assertRaises(AccessError):
            self.project.with_user(self.executor).action_enable_git_policy_apply()
        preview = (
            self.rule.with_user(self.author)
            .with_context(task_id=999, model="res.users")
            .action_preview()
        )
        self.assertEqual(preview["res_model"], "project.git.policy.evaluation")
        self.assertFalse(self.effects.search([]))

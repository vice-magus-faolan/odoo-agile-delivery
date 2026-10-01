"""Apply regressions using the same trusted synthetic ledger as the dry run."""
from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged

from .test_policy_evaluation import TestGitPolicyEvaluation


@tagged("post_install", "-at_install")
class TestGitPolicyApply(TestGitPolicyEvaluation):
    def setUp(self):
        super().setUp()
        self.project.with_user(self.author).action_enable_git_policy(mode="apply")
        self._successor()
        self.attempts = self.env["project.git.policy.attempt"]
        self.effects = self.env["project.git.policy.effect"]

    def _discover(self):
        with patch.object(fields.Datetime, "now", return_value=self.now):
            return self.attempts.with_user(self.author)._discover_repository(self.repository.with_user(self.author), 0)[0]

    def _apply(self):
        with patch.object(fields.Datetime, "now", return_value=self.now):
            attempt = self.attempts._claim_attempt()
            if attempt:
                attempt._process_claim()
            return attempt

    def test_apply_exact_stage_only_and_semantic_replay(self):
        before = self.task.read(["agile_key", "agile_story_points", "parent_id"])
        attempt = self._discover()
        self.assertEqual(attempt.state, "queued")
        self.assertEqual(attempt.expected_transition_version, self.task.git_policy_transition_version)
        self.assertEqual(self._apply(), attempt)
        self.assertEqual(attempt.state, "applied", attempt.reason)
        self.assertEqual(self.task.stage_id, self.stages[1])
        self.assertFalse(self.task.is_closed)
        self.assertEqual(before, self.task.read(["agile_key", "agile_story_points", "parent_id"]))
        effect = self.effects.search([])
        self.assertEqual(len(effect), 1)
        self.assertEqual(effect.execution_user_id, self.executor)
        self.assertEqual(effect.before_stage_id, self.stages[0])
        self.assertEqual(effect.after_stage_id, self.stages[1])
        self.assertEqual(self.task.write_uid, self.executor)
        self.assertEqual(attempt.event_ids.mapped("reason"), ["no_ci_condition", "applied"])
        self.task.with_user(self.author).write({"stage_id": self.stages[0].id})
        self._successor()
        self._discover()
        self._apply()
        self.assertEqual(self.task.stage_id, self.stages[0])
        self.assertEqual(self.effects.search_count([]), 1)

    def test_away_and_back_is_a_terminal_fence_conflict(self):
        attempt = self._discover()
        version = self.task.git_policy_transition_version
        self.task.with_user(self.executor).write({"stage_id": self.stages[2].id})
        self.task.with_user(self.executor).write({"stage_id": self.stages[0].id})
        self.assertGreater(self.task.git_policy_transition_version, version)
        self._apply()
        self.assertEqual((attempt.state, attempt.reason), ("rejected", "stale_task"))
        self.assertFalse(self.effects.search([]))
        self._discover()
        self.assertEqual(self.attempts.search_count([]), 1)

    def test_disable_revision_and_revocation_stop_claimed_work(self):
        attempt = self._discover()
        self.project.with_user(self.author).action_disable_git_policy()
        self._apply()
        self.assertEqual(attempt.state, "revoked")
        self.assertEqual(self.task.stage_id, self.stages[0])
        self.assertFalse(self.effects.search([]))

    def test_cutoff_and_current_evidence_are_rechecked(self):
        attempt = self._discover()
        self.pr.write({"merged_at": self.cutoff})
        self._apply()
        self.assertEqual(attempt.state, "rejected")
        self.assertFalse(self.effects.search([]))

    def test_waiting_check_wakes_existing_attempt_without_new_fence(self):
        self._required()
        attempt = self._discover()
        self.assertEqual(attempt.state, "waiting")
        self._check()
        self.now += timedelta(minutes=2)
        self._apply()
        self.assertEqual(attempt.state, "applied")
        self.assertEqual(self.attempts.search_count([]), 1)

    def test_partial_batch_failure_rolls_back_task_effect_and_audit(self):
        first = self._discover()
        effect_class = type(self.effects)
        with patch.object(effect_class, "_append", side_effect=RuntimeError("secret should never be stored")):
            self._apply()
        self.assertEqual(first.state, "retryable")
        self.assertEqual(self.task.stage_id, self.stages[0])
        self.assertFalse(self.effects.search([]))
        self.assertEqual(first.reason, "transient_failure")
        self.assertNotIn("secret", str(first.event_ids.read()))
        self.now += timedelta(minutes=2)
        self._apply()
        self.assertEqual(first.state, "applied")
        self.assertEqual(self.effects.search_count([]), 1)

    def test_expired_lease_and_bounded_dead_letter(self):
        attempt = self._discover()
        claimed = self.attempts._claim_attempt()
        self.assertEqual(claimed, attempt)
        token = claimed.lease_token
        self.assertFalse(self.attempts._claim_attempt())
        self.now += timedelta(minutes=6)
        with patch.object(fields.Datetime, "now", return_value=self.now):
            renewed = self.attempts._claim_attempt()
        self.assertEqual(renewed, attempt)
        self.assertNotEqual(token, renewed.lease_token)
        renewed._process_claim()
        self.assertEqual(renewed.state, "applied")

    def test_public_and_forged_context_cannot_schedule_mutate_or_consume(self):
        attempt = self._discover()
        for model in (self.attempts, self.effects, self.env["project.git.policy.attempt.event"]):
            with self.assertRaises(AccessError):
                model.with_user(self.author).with_context(policy_trusted=True).create({})
        for item in (attempt,):
            with self.assertRaises(AccessError):
                item.with_user(self.author).write({"state": "queued"})
            with self.assertRaises(ValidationError):
                item.unlink()
        with self.assertRaises(ValidationError):
            self.task.with_context(policy_trusted=True).write({"git_policy_transition_version": 0})
        with self.assertRaises(ValidationError):
            self.env["project.task"].create({"name": "Forged fence", "git_policy_transition_version": 9})

    def test_current_nonadmin_record_authority_and_multicompany_visibility(self):
        attempt = self._discover()
        self.executor.active = False
        self._apply()
        self.assertEqual(attempt.state, "revoked")
        self.assertFalse(self.effects.search([]))
        hidden = self.env["ir.rule"].create({
            "name": "Hide concrete task", "model_id": self.env["ir.model"]._get("project.task").id,
            "domain_force": "[('name', '=', 'invisible')]",
        })
        reader = attempt.with_user(self.author)
        self.assertFalse(reader.search([("id", "=", attempt.id)]))
        self.assertEqual(reader.search_count([("id", "=", attempt.id)]), 0)
        with self.assertRaises(AccessError):
            reader.read(["reason"])
        hidden.unlink()

    def test_dry_run_never_schedules_and_closed_tasks_never_apply(self):
        self.project.with_user(self.author).action_enable_git_policy(mode="dry_run")
        self._successor()
        self.assertFalse(self._discover())
        self.assertFalse(self.effects.search([]))
        self.project.with_user(self.author).action_enable_git_policy(mode="apply")
        self._successor()
        self.task.state = "1_done"
        self._discover()
        self._apply()
        self.assertFalse(self.effects.search([]))
        self.assertEqual(self.task.state, "1_done")

    def test_scrum_closed_sprint_history_is_unchanged(self):
        if "sprint_id" not in self.task._fields:
            self.skipTest("Optional Scrum is not installed in standalone fixture")
        item_type = self.env["project.agile.item.type"].search([("can_schedule_in_sprint", "=", True)], limit=1)
        self.task.agile_item_type_id = item_type
        team = self.env["project.agile.team"].create({"name": "Apply team", "project_id": self.project.id})
        sprint = self.env["project.sprint"].create({"name": "Apply scope", "project_id": self.project.id, "team_id": team.id})
        self.task.sprint_id = sprint
        sprint.action_start()
        self.task.state = "1_done"
        sprint._close_with_disposition("product_backlog")
        self.task.state = "01_in_progress"
        before = sprint.read()
        history = self.env["project.sprint.scope.event"].search([("task_id", "=", self.task.id)]).read()
        self._discover()
        attempt = self._apply()
        self.assertEqual(attempt.state, "applied", attempt.reason)
        self.assertEqual(self.task.stage_id, self.stages[1])
        self.assertEqual(self.effects.search_count([]), 1)
        self.assertEqual(self.task.sprint_id, sprint)
        self.assertEqual(before, sprint.read())
        self.assertEqual(history, self.env["project.sprint.scope.event"].search([("task_id", "=", self.task.id)]).read())

    def test_dry_run_to_apply_uses_new_cutoff_not_the_old_proposal(self):
        self.project.with_user(self.author).action_enable_git_policy(mode="dry_run")
        self._successor()
        before_version = self.task.git_policy_transition_version
        decision = self._evaluate()
        self.assertEqual(decision.outcome, "matched")
        self.assertFalse(self._discover())
        self.project.with_user(self.author).action_enable_git_policy(mode="apply")
        self.cutoff = self.now
        self._successor()
        self.assertGreater(self.activation.activated_at, decision.activation_id.activated_at)
        self.assertFalse(self._discover())
        self.assertFalse(self._apply())
        self.assertFalse(self.effects.search([]))
        self.assertEqual(self.task.stage_id, self.stages[0])
        self.assertEqual(self.task.git_policy_transition_version, before_version)

    def test_native_state_recompute_does_not_create_active_sprint_completion(self):
        if "sprint_id" not in self.task._fields:
            self.skipTest("Optional Scrum is not installed in standalone fixture")
        item_type = self.env["project.agile.item.type"].search([("can_schedule_in_sprint", "=", True)], limit=1)
        self.task.agile_item_type_id = item_type
        team = self.env["project.agile.team"].create({"name": "Active apply team", "project_id": self.project.id})
        sprint = self.env["project.sprint"].create({"name": "Active apply scope", "project_id": self.project.id, "team_id": team.id})
        self.task.sprint_id = sprint
        sprint.action_start()
        self.task.state = "03_approved"
        history = self.env["project.sprint.scope.event"].search([("task_id", "=", self.task.id)]).read()
        self._discover()
        attempt = self._apply()
        self.assertEqual(attempt.state, "applied", attempt.reason)
        self.assertEqual(self.task.stage_id, self.stages[1])
        self.assertEqual(self.task.state, "01_in_progress")
        self.assertEqual(self.task.sprint_id, sprint)
        self.assertEqual(history, self.env["project.sprint.scope.event"].search([("task_id", "=", self.task.id)]).read())

    def test_applied_event_failure_rolls_back_effect_and_native_stage(self):
        attempt = self._discover()
        event_class = type(self.env["project.git.policy.attempt.event"])
        append = event_class._append
        def fail_applied(events, item, state, reason):
            if state == "applied":
                raise RuntimeError("synthetic private failure")
            return append(events, item, state, reason)
        before_version = self.task.git_policy_transition_version
        with patch.object(event_class, "_append", fail_applied):
            self._apply()
        self.assertEqual(attempt.state, "retryable")
        self.assertEqual(self.task.stage_id, self.stages[0])
        self.assertEqual(self.task.git_policy_transition_version, before_version)
        self.assertFalse(self.effects.search([]))
        self.assertNotIn("applied", attempt.event_ids.mapped("state"))

    def test_dead_letter_after_five_failures_is_bounded(self):
        attempt = self._discover()
        with patch.object(type(self.effects), "_append", side_effect=RuntimeError("synthetic failure")):
            for count in range(5):
                self._apply()
                self.assertEqual(attempt.attempt_count, count + 1)
                self.now += timedelta(hours=1)
        self.assertEqual((attempt.state, attempt.reason), ("failed", "transient_failure"))
        self.assertFalse(self._apply())
        self.assertEqual(len(attempt.event_ids), 6)
        self.assertFalse(self.effects.search([]))

    def test_partial_batch_keeps_second_task_independent(self):
        other = self.env["project.task"].create({"name": "Other apply", "project_id": self.project.id, "stage_id": self.stages[0].id})
        self._associate(other, self.pr, self.delivery)
        self._successor()
        attempts = self._discover()
        self.assertEqual(len(attempts), 2)
        with patch.object(type(self.effects), "_append", side_effect=RuntimeError("one item fails")):
            first = self._apply()
        second = self._apply()
        self.assertEqual((first.state, second.state), ("retryable", "applied"))
        self.assertEqual(self.effects.search_count([]), 1)
        self.assertEqual(first.task_id.stage_id, self.stages[0])
        self.assertEqual(second.task_id.stage_id, self.stages[1])

    def test_conflicting_apply_rules_do_not_pick_a_first_match(self):
        self._rule()
        attempts = self._discover()
        self.assertEqual(len(attempts), 2)
        self.assertEqual(set(attempts.mapped("reason")), {"conflicting_rules"})
        self.assertFalse(self._apply())
        self.assertFalse(self.effects.search([]))

    def test_revoked_revision_and_target_settings_are_rechecked(self):
        attempt = self._discover()
        self.revision.action_new_revision()
        self._apply()
        self.assertEqual(attempt.state, "revoked")
        self.assertFalse(self.effects.search([]))

    def test_manual_target_never_consumes_an_effect(self):
        attempt = self._discover()
        self.task.stage_id = self.stages[1]
        self._apply()
        self.assertEqual(attempt.reason, "stale_task")
        self.assertFalse(self.effects.search([]))

    def test_stale_lease_token_cannot_use_a_reclaimed_lease(self):
        attempt = self._discover()
        original = self.attempts._claim_attempt()
        token = original.lease_token
        self.now += timedelta(minutes=6)
        with patch.object(fields.Datetime, "now", return_value=self.now):
            renewed = self.attempts._claim_attempt()
            renewed._process_claim(token)
            self.assertEqual(renewed.state, "processing")
            self.assertFalse(self.effects.search([]))
            renewed._process_claim(renewed.lease_token)
        self.assertEqual(attempt.state, "applied")

    def test_unknown_write_monkeypatch_is_rejected_before_business_write(self):
        attempt = self._discover()
        original = type(self.task).write
        calls = []
        def unreviewed(tasks, values):
            calls.append(values)
            return original(tasks, values)
        with patch.object(type(self.task), "write", unreviewed):
            self._apply()
        self.assertEqual(attempt.reason, "unsupported_extension")
        self.assertFalse(calls)
        self.assertFalse(self.effects.search([]))

    def test_effect_and_event_are_immutable_and_task_visible_only(self):
        self._discover()
        attempt = self._apply()
        effect = self.effects.search([])
        for item in (effect, attempt.event_ids):
            with self.assertRaises(ValidationError):
                item.write({})
            with self.assertRaises(ValidationError):
                item.unlink()
        company = self.env["res.company"].create({"name": "Apply second company"})
        self.author.company_ids = [Command.link(company.id)]
        rule = self.env["ir.rule"].create({
            "name": "Hide Task from all native readers", "model_id": self.env["ir.model"]._get("project.task").id,
            "domain_force": "[('name', '=', 'not this task')]",
        })
        for item in (attempt, effect, attempt.event_ids):
            scoped = item.with_user(self.author).with_context(allowed_company_ids=[self.env.company.id, company.id])
            domain = [("id", "in", item.ids)]
            self.assertFalse(scoped.search(domain))
            self.assertEqual(scoped.search_count(domain), 0)
            self.assertEqual(scoped._read_group(domain, [], ["__count"])[0][0], 0)
            with self.assertRaises(AccessError):
                scoped.read(["task_id"])
            with self.assertRaises(AccessError):
                scoped.export_data(["task_id"])
        rule.unlink()

    def test_native_progress_cannot_commit_from_model_or_rpc_context(self):
        scheduler = self.env["project.git.policy.schedule"]
        with self.assertRaises(AccessError):
            scheduler._cron_process_git_policy()
        with self.assertRaises(AccessError):
            scheduler.with_context(cron_id=1, ir_cron_progress_id=2147483647)._cron_process_git_policy()

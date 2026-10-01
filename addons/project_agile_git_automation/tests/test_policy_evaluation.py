"""Discovered dry-run tests over synthetic trusted ledger facts, never live ingress."""

from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGitPolicyEvaluation(TransactionCase):
    def setUp(self):
        super().setUp()
        cap = "project_agile_git_automation.group_git_policy_manager"
        self.author = mail_new_test_user(self.env, "eval_author", groups=cap + ",base.group_allow_export")
        self.approver = mail_new_test_user(self.env, "eval_approver", groups=cap)
        self.executor = mail_new_test_user(self.env, "eval_executor", groups="project.group_project_user")
        self.project = self.env["project.project"].create({
            "name": "Evaluation", "company_id": self.env.company.id, "agile_enabled": True,
            "agile_key": "EVA", "privacy_visibility": "employees",
        })
        self.repository = self.env["project.git.repository"].create({
            "name": "Evaluation", "provider": "github", "provider_repository_id": "evaluation",
            "canonical_url": "https://github.com/synthetic/evaluation", "project_id": self.project.id,
        })
        self.stages = self.env["project.task.type"].create([
            {"name": n, "project_ids": [Command.link(self.project.id)]} for n in ("Develop", "QA", "Other")
        ])
        self.task = self.env["project.task"].create({
            "name": "Evaluation task", "project_id": self.project.id, "stage_id": self.stages[0].id,
        })
        self.now = fields.Datetime.now()
        self.cutoff = self.now - timedelta(hours=1)
        self.merged = self.now - timedelta(minutes=30)
        self.rule, self.revision, self.activation = self._rule()
        self.delivery = self._delivery("pr-delivery", "pull_request")
        self.pr = self.env["project.git.pull.request"].create({
            "repository_id": self.repository.id, "provider_request_id": "pr-one", "state": "merged",
            "target_branch": "main", "head_sha": "a" * 40, "merged_at": self.merged,
            "updated_at": self.merged, "ordering_state": "known", "provenance_delivery_id": self.delivery.id,
        })
        self.association, self.association_audit = self._associate(self.task, self.pr, self.delivery)

    def _rule(self, checks=()):
        rule = self.env["project.git.policy.rule"].with_user(self.author).create({
            "name": "Merged to QA", "repository_id": self.repository.id,
        })
        revision = self.env["project.git.policy.revision"].with_user(self.author).create({
            "rule_id": rule.id, "target_branch": "main", "allowed_source_stage_ids": [Command.set(self.stages[:1].ids)],
            "target_stage_id": self.stages[1].id, "execution_user_id": self.executor.id,
            "required_check_ids": [Command.create({"name": n}) for n in checks],
        })
        if not self.project.git_policy_enabled:
            self.project.with_user(self.author).action_enable_git_policy()
        with patch.object(fields.Datetime, "now", return_value=self.cutoff):
            result = revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)
        return rule, revision, self.env["project.git.policy.activation"].browse(result["activation_id"])

    def _delivery(self, identity, event):
        return self.env["project.git.delivery"].create({
            "repository_id": self.repository.id, "provider_delivery_id": identity,
            "event_type": event, "payload_sha256": "b" * 64, "payload_size": 300,
            "state": "processed", "processed_at": self.now - timedelta(minutes=20),
            "received_at": self.now - timedelta(minutes=25), "attempt_count": 1,
        })

    def _associate(self, task, pr, delivery):
        association = self.env["project.git.task.association"].create({
            "repository_id": self.repository.id, "task_id": task.id,
            "source_type": "pull_request", "source_provider_id": pr.provider_request_id,
        })
        audit = self.env["project.git.association.audit"].create({
            "repository_id": self.repository.id, "task_id": task.id, "delivery_id": delivery.id,
            "source_type": "pull_request", "source_provider_id": pr.provider_request_id,
            "source_field": "title", "agile_key": task.agile_key,
            "outcome": "associated", "reason": "exact_key",
        })
        return association, audit

    def _check(self, identity="check-one", name="unit", **values):
        delivery = self._delivery(identity + "-delivery", "check_run")
        return self.env["project.git.check"].create({
            "repository_id": self.repository.id, "provider_check_id": identity, "name": name,
            "head_sha": self.pr.head_sha, "state": "success", "ordering_state": "known",
            "updated_at": self.merged, "completed_at": self.merged,
            "provenance_delivery_id": delivery.id, **values,
        })

    def _required(self):
        self._successor(("unit",))

    def _successor(self, checks=()):
        result = self.revision.action_new_revision()
        self.revision = self.revision.browse(result["res_id"])
        if checks:
            self.revision.write({"required_check_ids": [Command.create({"name": n}) for n in checks]})
        with patch.object(fields.Datetime, "now", return_value=self.cutoff):
            result = self.revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)
        self.activation = self.env["project.git.policy.activation"].browse(result["activation_id"])

    def _evaluate(self):
        with patch.object(fields.Datetime, "now", return_value=self.now):
            result = self.repository.with_user(self.author).action_dry_run_git_policy()
        self.assertEqual(result["type"], "ir.actions.act_window")
        return self.env["project.git.policy.evaluation"].search([], order="id desc", limit=1)

    def test_sealed_match_is_immutable_deduplicated_and_effect_free(self):
        before = self.task.read(["stage_id", "state", "write_date", "message_ids", "message_follower_ids", "agile_story_points"])
        facts = self.pr.read() + self.delivery.read() + self.association.read() + self.association_audit.read()
        decision = self._evaluate()
        self.assertEqual((decision.outcome, decision.reason), ("matched", "no_ci_condition"))
        self.assertEqual(decision.mode, "dry_run")
        self.assertEqual(decision.task_id, self.task)
        self.assertEqual(decision.snapshot_version, 1)
        self.assertEqual(len(decision.fingerprint), 64)
        self.assertEqual(decision, self._evaluate())
        self.assertEqual(self.env["project.git.policy.evaluation"].search_count([]), 1)
        self.assertEqual(self.env["project.git.policy.observation"].search_count([]), 1)
        self.assertEqual(before, self.task.read(["stage_id", "state", "write_date", "message_ids", "message_follower_ids", "agile_story_points"]))
        self.assertEqual(facts, self.pr.read() + self.delivery.read() + self.association.read() + self.association_audit.read())
        for record in (decision, decision.observation_ids):
            with self.assertRaises(ValidationError):
                record.write({"fingerprint": "f" * 64})
            with self.assertRaises(ValidationError):
                record.unlink()
        self.assertNotIn("project.git.policy.effect", self.env.registry)
        self.assertNotIn("project.git.policy.attempt", self.env.registry)

    def test_public_create_and_forged_context_never_mint_a_seal(self):
        for model in ("project.git.policy.observation", "project.git.policy.evaluation"):
            for user in (self.author, self.executor, self.env.user):
                with self.subTest(model=model, user=user.id), self.assertRaises(AccessError):
                    self.env[model].with_user(user).with_context(authenticated=True, processed=True).create({})
        with self.assertRaises(AccessError):
            self.delivery.with_user(self.author).with_context(authenticated=True).write({"state": "processed"})
        with self.assertRaises(AccessError):
            self.repository.with_user(self.executor).action_dry_run_git_policy()
        with self.assertRaises(ValidationError):
            self.repository.with_user(self.author).action_dry_run_git_policy(after_id=True)

    def test_status_alone_does_not_make_a_settled_delivery(self):
        self.delivery.write({"processed_at": False})
        self.assertEqual(self._evaluate().reason, "invalid_provenance")
        self.assertFalse(self.env["project.git.policy.observation"].search([]))

    def test_unsettled_lease_and_wrong_event_are_rejected(self):
        self.delivery.write({"lease_token": "not-settled"})
        self.assertEqual(self._evaluate().reason, "invalid_provenance")
        self.delivery.write({"lease_token": False, "event_type": "push"})
        self.assertEqual(self._evaluate().reason, "invalid_provenance")

    def test_old_association_is_not_current_pr_evidence(self):
        newer = self._delivery("pr-new", "pull_request")
        self.pr.write({"provenance_delivery_id": newer.id})
        self.assertEqual(self._evaluate().reason, "invalid_provenance")
        self.env["project.git.association.audit"].create({
            "repository_id": self.repository.id, "task_id": self.task.id, "delivery_id": newer.id,
            "source_type": "pull_request", "source_provider_id": self.pr.provider_request_id,
            "source_field": "body", "agile_key": self.task.agile_key,
            "outcome": "already_associated", "reason": "duplicate",
        })
        self.assertEqual(self._evaluate().outcome, "matched")

    def test_exact_branch_head_and_order_are_fail_closed(self):
        for value, reason in (("MAIN", "branch_mismatch"), ("main ", "branch_mismatch")):
            self.pr.write({"target_branch": value})
            self.assertEqual(self._evaluate().reason, reason)
        self.pr.write({"target_branch": "main", "head_sha": "a" * 39})
        self.assertEqual(self._evaluate().reason, "invalid_provenance")
        self.pr.write({"head_sha": "a" * 40, "ordering_state": "ambiguous"})
        self.assertEqual(self._evaluate().reason, "ambiguous_order")
        self.pr.write({"ordering_state": "stale"})
        self.assertEqual(self._evaluate().reason, "ambiguous_order")

    def test_cutoff_source_receipt_equality_and_future_fail_closed(self):
        for field, value, reason in (
            ("merged_at", self.cutoff, "before_cutoff"),
            ("merged_at", self.cutoff - timedelta(seconds=1), "before_cutoff"),
            ("merged_at", self.now + timedelta(seconds=1), "invalid_time"),
            ("updated_at", False, "invalid_time"),
            ("updated_at", self.now + timedelta(seconds=1), "invalid_time"),
        ):
            self.pr.write({"merged_at": self.merged, "updated_at": self.merged, field: value})
            self.assertEqual(self._evaluate().reason, reason)
        self.pr.write({"merged_at": self.merged, "updated_at": self.merged})
        self.delivery.write({"received_at": self.cutoff})
        self.assertEqual(self._evaluate().reason, "before_cutoff")
        self.delivery.write({"received_at": self.cutoff - timedelta(days=1)})
        self.assertEqual(self._evaluate().reason, "before_cutoff")

    def test_candidate_expires_without_receipt_refresh_extending_it(self):
        self.now += timedelta(days=2)
        self.assertEqual(self._evaluate().reason, "expired")
        self.pr.write({"last_seen_at": self.now})
        self.assertEqual(self._evaluate().reason, "expired")

    def test_missing_then_late_check_rechecks_exact_sha(self):
        self._required()
        self.assertEqual(self._evaluate().outcome, "waiting")
        self._check(head_sha="c" * 40)
        self.assertEqual(self._evaluate().reason, "missing_check")
        self._check("late", head_sha=self.pr.head_sha)
        self.assertEqual((self._evaluate().outcome, self._evaluate().reason), ("matched", "checks_passed"))

    def test_failed_neutral_unknown_and_pending_checks(self):
        self._required()
        check = self._check()
        for state, outcome, reason in (
            ("pending", "waiting", "pending_check"), ("running", "waiting", "pending_check"),
            ("failure", "rejected", "check_failed"), ("cancelled", "rejected", "check_failed"),
            ("neutral", "rejected", "check_failed"), ("unknown", "rejected", "ambiguous_check"),
            ("success", "matched", "checks_passed"),
        ):
            check.write({"state": state})
            self.assertEqual((self._evaluate().outcome, self._evaluate().reason), (outcome, reason))

    def test_check_timestamp_order_and_freshness_matrix(self):
        self._required()
        check = self._check()
        for values, reason in (
            ({"updated_at": False}, "ambiguous_check"),
            ({"completed_at": False}, "ambiguous_check"),
            ({"ordering_state": "ambiguous"}, "ambiguous_check"),
            ({"ordering_state": "stale"}, "ambiguous_check"),
            ({"completed_at": self.now + timedelta(seconds=1)}, "ambiguous_check"),
            ({"updated_at": self.now + timedelta(seconds=1)}, "ambiguous_check"),
            ({"completed_at": self.merged - timedelta(days=2)}, "ambiguous_check"),
        ):
            check.write({"updated_at": self.merged, "completed_at": self.merged, "ordering_state": "known", **values})
            self.assertEqual(self._evaluate().reason, reason)

    def test_same_name_reruns_remain_ambiguous_even_with_newer_success(self):
        self._required()
        self._check(state="failure")
        self._check("999999", updated_at=self.now, completed_at=self.now)
        decision = self._evaluate()
        self.assertEqual((decision.outcome, decision.reason), ("rejected", "ambiguous_check"))

    def test_conflicting_rules_even_identical_targets_do_not_choose_order(self):
        self._rule()
        decisions = self._evaluate()
        self.assertEqual((decisions.outcome, decisions.reason), ("conflicted", "conflicting_rules"))
        self.assertEqual(self.env["project.git.policy.evaluation"].search_count([]), 2)
        self.assertEqual(self.task.stage_id, self.stages[0])

    def test_manual_stage_change_is_stale_and_already_target_is_noop(self):
        self._evaluate()
        self.task.with_user(self.author).write({"stage_id": self.stages[2].id})
        self.assertEqual(self._evaluate().reason, "stale_task")
        self.task.with_user(self.author).write({"stage_id": self.stages[0].id})
        # Informational proposals never acquire apply eligibility; the apply phase adds its fence.
        self.task.with_user(self.author).write({"stage_id": self.stages[1].id})
        self.assertEqual(self._evaluate().reason, "stale_task")

    def test_archived_task_inactive_repo_disabled_and_revised_rules(self):
        self.task.write({"active": False})
        self.assertEqual(self._evaluate().reason, "inactive_task")
        self.task.write({"active": True})
        self.assertEqual(self._evaluate().reason, "inactive_policy")
        self.repository.write({"active": False})
        self.assertEqual(self._evaluate().reason, "inactive_repository")

    def test_multiple_prs_and_tasks_are_distinct_but_duplicate_polls_are_not(self):
        task = self.env["project.task"].create({"name": "Second", "project_id": self.project.id, "stage_id": self.stages[0].id})
        # Task creation revokes the first epoch; approve a single successor rule.
        self._successor()
        self._associate(task, self.pr, self.delivery)
        delivery = self._delivery("pr-two", "pull_request")
        pr = self.env["project.git.pull.request"].create({
            "repository_id": self.repository.id, "provider_request_id": "pr-two", "state": "merged",
            "head_sha": self.pr.head_sha, "target_branch": "main", "merged_at": self.merged,
            "updated_at": self.merged, "ordering_state": "known", "provenance_delivery_id": delivery.id,
        })
        self._associate(self.task, pr, delivery)
        self._evaluate()
        self.assertEqual(self.env["project.git.policy.evaluation"].search_count([]), 3)
        self._evaluate()
        self.assertEqual(self.env["project.git.policy.evaluation"].search_count([]), 3)

    def test_hidden_task_rows_counts_grouping_and_exports_use_native_rules(self):
        decision = self._evaluate()
        self.env["ir.rule"].create({
            "name": "Hide evaluation Task", "model_id": self.env["ir.model"]._get("project.task").id,
            "domain_force": "[('name', '!=', 'Evaluation task')]",
        })
        for model in ("project.git.policy.evaluation", "project.git.policy.observation"):
            scoped = self.env[model].with_user(self.author)
            self.assertFalse(scoped.search([]))
            self.assertEqual(scoped.search_count([]), 0)
            self.assertFalse(scoped._read_group([], ["company_id"], ["__count"]))
        with self.assertRaises(AccessError):
            decision.with_user(self.author).read(["agile_key"])
        with self.assertRaises(AccessError):
            decision.with_user(self.author).export_data(["agile_key"])

    def test_multi_company_cross_repo_provenance_cannot_qualify(self):
        company = self.env["res.company"].create({"name": "Other evaluation company"})
        project = self.env["project.project"].with_context(allowed_company_ids=company.ids).create({
            "name": "Other", "company_id": company.id, "agile_enabled": True, "agile_key": "OTH",
        })
        repository = self.env["project.git.repository"].create({
            "name": "Other", "provider": "github", "provider_repository_id": "other-evaluation",
            "canonical_url": "https://github.com/synthetic/other", "project_id": project.id,
        })
        delivery = self.env["project.git.delivery"].create({
            "repository_id": repository.id, "provider_delivery_id": "other", "event_type": "pull_request",
            "payload_sha256": "d" * 64, "payload_size": 300, "state": "processed",
            "processed_at": self.now, "received_at": self.now, "attempt_count": 1,
        })
        # Company/security setup conservatively invalidates the earlier approval.
        self._successor()
        self.pr.write({"provenance_delivery_id": delivery.id})
        self.assertEqual(self._evaluate().reason, "invalid_provenance")
        with self.assertRaises(AccessError):
            repository.with_user(self.author).action_dry_run_git_policy()

    def test_bounded_twenty_task_page_and_deduplicated_poll_queries(self):
        tasks = self.env["project.task"].create([
            {"name": "Bounded task %s" % i, "project_id": self.project.id, "stage_id": self.stages[0].id}
            for i in range(19)
        ])
        self._successor()
        for task in tasks:
            self._associate(task, self.pr, self.delivery)
        count = self.cr.sql_log_count
        self._evaluate()
        cold = self.cr.sql_log_count - count
        self.assertEqual(self.env["project.git.policy.evaluation"].search_count([]), 20)
        count = self.cr.sql_log_count
        self._evaluate()
        warm = self.cr.sql_log_count - count
        self.assertLess(cold, 800)
        self.assertLess(warm, 200)
        self.assertEqual(self.env["project.git.policy.evaluation"].search_count([]), 20)

    def test_failure_is_not_hidden_by_an_earlier_pending_required_name(self):
        self._successor(("a-pending", "z-failed"))
        self._check(name="a-pending", state="pending")
        self._check("failed", name="z-failed", state="failure")
        self.assertEqual(self._evaluate().reason, "check_failed")

    def test_check_from_other_repository_with_exact_name_sha_cannot_qualify(self):
        repository = self.env["project.git.repository"].create({
            "name": "Other same Project", "provider": "github", "provider_repository_id": "other-same-project",
            "canonical_url": "https://github.com/synthetic/other-same-project", "project_id": self.project.id,
        })
        self._required()
        check = self._check(repository_id=repository.id)
        self.assertEqual(self._evaluate().reason, "missing_check")
        with self.assertRaises(ValidationError):
            self.env["project.git.policy.observation"].with_user(self.author)._seal(
                self.pr, self.task, self.association, self.association_audit, check, self.now,
            )

    def test_private_sealer_rejects_mixed_head_and_unsigned_receipt_shape(self):
        check = self._check(head_sha="c" * 40)
        with self.assertRaises(ValidationError):
            self.env["project.git.policy.observation"].with_user(self.author)._seal(
                self.pr, self.task, self.association, self.association_audit, check, self.now,
            )
        self.delivery.write({"payload_sha256": "not-a-digest"})
        self.assertEqual(self._evaluate().reason, "invalid_provenance")

    def test_raw_pr_strings_never_select_another_task(self):
        task = self.env["project.task"].create({"name": "Unassociated", "project_id": self.project.id})
        self._successor()
        self.pr.write({"title": task.agile_key, "source_branch": "feature/" + task.agile_key})
        decision = self._evaluate()
        self.assertEqual(decision.task_id, self.task)
        self.assertFalse(self.env["project.git.policy.evaluation"].search([("task_id", "=", task.id)]))

    def test_disabled_successor_and_stale_approval_never_revive_old_evaluation(self):
        initial = self._evaluate()
        self.rule.with_user(self.author).action_disable()
        self.assertEqual(self._evaluate().reason, "inactive_policy")
        with patch.object(fields.Datetime, "now", return_value=self.now):
            result = self.revision.action_new_revision()
            revision = self.revision.browse(result["res_id"])
            revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)
        self.assertEqual(self._evaluate().reason, "before_cutoff")
        self.assertNotEqual(initial.activation_id, self.rule.activation_id)

    def test_native_scrum_fields_and_scope_history_are_untouched(self):
        names = ["agile_story_points", "parent_id", "state", "stage_id", "write_date"]
        history = []
        if "sprint_id" in self.task._fields:
            names += ["sprint_id"]
            history = self.env["project.sprint.scope.event"].search([("task_id", "=", self.task.id)]).read()
        before = self.task.read(names)
        self._evaluate()
        self.assertEqual(before, self.task.read(names))
        if "sprint_id" in self.task._fields:
            self.assertEqual(history, self.env["project.sprint.scope.event"].search([("task_id", "=", self.task.id)]).read())

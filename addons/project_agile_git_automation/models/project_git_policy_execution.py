"""Apply only stage_id through native Task ORM under the approved real identity."""

import json

from psycopg2 import IntegrityError
from psycopg2.errors import DeadlockDetected, SerializationFailure

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .policy_authority import clean_context, require_capability
from .policy_evidence import MAX_BATCH, MAX_EVIDENCE
from .project_git_policy_attempt import MAX_ATTEMPTS

PROTECTED = (
    "agile_key",
    "agile_story_points",
    "parent_id",
    "agile_item_type_id",
    "sprint_id",
)


class PolicyPostconditionError(ValidationError):
    """A native extension crossed the permitted business-effect boundary."""


class ProjectGitPolicyAttempt(models.Model):
    _inherit = "project.git.policy.attempt"

    def action_retry(self):
        """Requeue one transient failure; never reset its budget, fence or identity.

        No parameters or context values can replace candidate evidence. Terminal,
        leased, stale, revoked, expired and consumed work cannot be revived.
        Native cron independently revalidates again before any business effect.
        """
        self.ensure_one()
        require_capability(self.env)
        # Retry must not inherit caller-selected defaults or authority hints.
        # pylint: disable-next=context-overridden
        attempt = self.with_context(clean_context(self.env))
        attempt.check_access("read")
        attempt.rule_id._check_control()
        attempt = attempt.try_lock_for_update()
        if not attempt:
            raise ValidationError(_("This attempt is currently being processed."))
        require_capability(attempt.env)
        attempt.check_access("read")
        attempt.rule_id._check_control()
        attempt._check_retry_candidate()
        attempt._set_schedule(
            {
                "state": "queued",
                "reason": "operator_retry",
                "next_retry_at": False,
                "lease_token": False,
                "lease_expires_at": False,
            }
        )
        attempt._append_event("queued", "operator_retry")
        return True

    def _check_retry_candidate(self):
        """Read-only eligibility; apply independently revalidates before publication."""
        if (
            self.state != "retryable"
            or self.reason != "transient_failure"
            or self.attempt_count >= MAX_ATTEMPTS
        ):
            raise ValidationError(
                _("Only an unexhausted transient failure can be retried.")
            )
        if self.env["project.git.policy.effect"]._consumed(
            self.repository_id, self.provider_request_id, self.agile_key
        ):
            raise ValidationError(_("This PR/Task effect has already been consumed."))
        try:
            result, _observation = self._current_candidate(
                self.repository_id, self.task_id
            )
        except (AccessError, ValidationError) as error:
            raise ValidationError(
                _("Retry requires unchanged current approval and evidence.")
            ) from error
        if result[0] not in {"matched", "waiting"}:
            raise ValidationError(
                _("Retry requires unchanged Task fence, cutoff and eligible evidence.")
            )

    @api.model
    def _candidate_page(self, repository, after_id):
        """Shared proven evidence predicates; apply proposals are never dry-run rows."""
        evaluator = self.env["project.git.policy.evaluation"]
        prs, rules, associations, audits, checks, tasks, _, overflow = (
            evaluator._load_batch(repository, after_id)
        )
        rules = rules.filtered(lambda r: r.activation_id.mode == "apply")
        authority = evaluator._authority_map(rules, tasks)
        candidates = []
        if not prs:
            return [], after_id, False
        pr = prs[0]
        associated = associations.filtered(
            lambda a: a.source_provider_id == pr.provider_request_id
        )
        local_tasks = tasks.filtered(lambda t: t.id in associated.task_id.ids)
        overflow = overflow or len(local_tasks) > MAX_EVIDENCE
        for task in local_tasks.sorted("id")[:MAX_EVIDENCE]:
            choices = []
            for rule in rules:
                result, observation = evaluator._candidate(
                    repository,
                    rule,
                    pr,
                    task,
                    associated,
                    audits,
                    checks,
                    None,
                    overflow,
                    authority[rule.id],
                    fields.Datetime.now(),
                )
                choices.append((rule, result, observation))
            matched = sum(result[0] == "matched" for _, result, _ in choices)
            for rule, result, observation in choices:
                if result[0] == "matched" and matched > 1:
                    result = ("conflicted", "conflicting_rules")
                if observation and result[0] in {"matched", "waiting", "conflicted"}:
                    candidates.append(
                        (rule.activation_id, pr, task, observation, result)
                    )
        return candidates, pr.id, overflow or len(candidates) > MAX_BATCH

    @api.model
    def _discover_repository(self, repository, after_id):
        """One bounded PR page; no partial overflow winner and no old attempt
        revival.
        """
        repository.check_access("read")
        repository.project_id.check_access("read")
        candidates, cursor, overflow = self._candidate_page(repository, after_id)
        attempts = self.browse()
        if overflow:
            return attempts, cursor, "evidence_limit"
        for activation, pr, task, observation, result in candidates:
            if self.env["project.git.policy.effect"]._consumed(
                repository, pr.provider_request_id, task.agile_key
            ):
                continue
            attempts |= self._enqueue(activation, pr, task, observation, result)
        return attempts, cursor, "no_ci_condition"

    def _current_candidate(self, repository, task):
        """Query native access/evidence before shared-row effect publication."""
        activation = self.activation_id.with_env(repository.env)
        activation._check_current_authority(task)
        if activation.mode != "apply":
            return ("revoked", "inactive_policy"), self.env[
                "project.git.policy.observation"
            ]
        if (
            task.agile_key != self.agile_key
            or task.stage_id != self.expected_stage_id
            or task.git_policy_transition_version != self.expected_transition_version
        ):
            return ("rejected", "stale_task"), self.env[
                "project.git.policy.observation"
            ]
        candidates, _, overflow = repository.env[
            "project.git.policy.attempt"
        ]._candidate_page(repository, self.pull_request_id.id - 1)
        if overflow:
            return ("rejected", "evidence_limit"), self.env[
                "project.git.policy.observation"
            ]
        choices = [
            row
            for row in candidates
            if row[0] == activation
            and row[1].id == self.pull_request_id.id
            and row[2] == task
        ]
        if not choices:
            # Repeat finite predicates for terminal provenance/cutoff diagnostics.
            evaluator = repository.env["project.git.policy.evaluation"]
            prs, _, links, audits, checks, _, _, overflow = evaluator._load_batch(
                repository, self.pull_request_id.id - 1
            )
            pr = prs.filtered(lambda p: p.id == self.pull_request_id.id)
            if not pr:
                return ("rejected", "invalid_provenance"), self.env[
                    "project.git.policy.observation"
                ]
            result, observation = evaluator._candidate(
                repository,
                activation.rule_id,
                pr,
                task,
                links,
                audits,
                checks,
                None,
                overflow,
                True,
                fields.Datetime.now(),
            )
            state = "expired" if result[1] == "expired" else "rejected"
            return (state, result[1]), observation
        _, _, _, observation, result = choices[0]
        if result[0] == "conflicted":
            return ("rejected", result[1]), observation
        old = json.loads(self.observation_id.snapshot_json)["pr"]
        current = json.loads(observation.snapshot_json)["pr"]
        if any(
            old[name] != current[name]
            for name in (
                "head_sha",
                "merged_at",
                "target_branch",
                "provider_request_id",
            )
        ):
            return ("rejected", "evidence_changed"), observation
        return result, observation

    def _has_current_lease(self, expected_token):
        """Check private claim ownership only after the native attempt lock."""
        return bool(
            expected_token
            and self.state == "processing"
            and self.lease_token == expected_token
            and self.lease_expires_at
            and self.lease_expires_at > fields.Datetime.now()
        )

    def _execute_locked(self, expected_token):
        self.ensure_one()
        # Private lease processing must discard caller context completely.
        service = self.sudo().with_context({})  # pylint: disable=context-overridden
        service = service.try_lock_for_update()
        if not service:
            return
        activation = service.activation_id
        if not service._has_current_lease(expected_token):
            return
        if service.env["project.git.policy.effect"]._consumed(
            service.repository_id, service.provider_request_id, service.agile_key
        ):
            service._settle("no_op", "consumed_effect")
            return
        # Clean context and with_user remove cron/root authority. No caller context,
        # notification suppression or Task sudo reaches the business write.
        # Replacement retains only the approved company's scope.
        # pylint: disable-next=context-overridden
        repository = service.repository_id.with_user(activation.owner_id).with_context(
            {
                "allowed_company_ids": service.company_id.ids,
            }
        )
        task = (
            repository.env["project.task"]
            .with_user(activation.execution_user_id)
            .browse(service.task_id.id)
        )
        try:
            result, observation = service._current_candidate(repository, task)
        except (AccessError, ValidationError):
            service._settle("revoked", "invalid_authority")
            return
        if result[0] != "matched":
            service._settle(
                "waiting" if result[0] == "waiting" else result[0], result[1]
            )
            return
        service._write_stage_effect(task, observation)

    def _write_stage_effect(self, task, observation):
        """Already revalidated; preserve native effects then publish shared activity
        atomically.
        """
        service = self
        activation = service.activation_id
        before = {
            "stage_id": task.stage_id.id,
            "state": task.state,
            "version": task.git_policy_transition_version,
            "protected": task.read(
                [name for name in PROTECTED if name in task._fields]
            )[0],
        }
        task.check_access("read")
        task.check_access("write")
        task.write({"stage_id": activation.revision_id.target_stage_id.id})
        task.flush_recordset()
        task.invalidate_recordset()
        if task.is_closed or task.stage_id != activation.revision_id.target_stage_id:
            raise PolicyPostconditionError(
                _("Native Task effects crossed the permitted stage boundary.")
            )
        if (
            before["protected"]
            != task.read([name for name in PROTECTED if name in task._fields])[0]
        ):
            raise PolicyPostconditionError(
                _("Native Task effects changed protected Agile/Scrum fields.")
            )
        service.env["project.git.policy.effect"]._append(
            service, observation, task, before
        )
        service._settle("applied", "applied")

    def _process_claim(self, lease_token=None):
        """Task/effect/event/settlement all share one savepoint.

        Failure does not leak text.
        """
        self.ensure_one()
        expected_token = (
            lease_token if lease_token is not None else self.sudo().lease_token
        )
        try:
            with self.env.cr.savepoint():
                self._execute_locked(expected_token)
        except (SerializationFailure, DeadlockDetected):
            # A savepoint rollback cannot refresh repeatable-read. The native cron
            # transaction must retry from a new cursor, never settle stale evidence.
            raise
        except PolicyPostconditionError:
            self._settle("failed", "postcondition_failed")
        except IntegrityError:
            if self.env["project.git.policy.effect"]._consumed(
                self.repository_id, self.provider_request_id, self.agile_key
            ):
                self._settle("no_op", "consumed_effect")
            else:
                self._settle(
                    "failed" if self.attempt_count >= MAX_ATTEMPTS else "retryable",
                    "transient_failure",
                )
        except Exception:
            self._settle(
                "failed" if self.attempt_count >= MAX_ATTEMPTS else "retryable",
                "transient_failure",
            )

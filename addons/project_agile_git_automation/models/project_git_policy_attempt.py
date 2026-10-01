"""Durable bounded scheduling; callers cannot manufacture an executable proposal."""
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL

from .policy_authority import lock_records
from .policy_evidence import MAX_BATCH, REASONS

STATES = [(n, n.replace("_", " ").title()) for n in (
    "queued", "waiting", "processing", "retryable", "failed", "rejected", "applied",
    "no_op", "revoked", "expired",
)]
ATTEMPT_REASONS = REASONS + [(n, n.replace("_", " ").title()) for n in (
    "applied", "consumed_effect", "transient_failure", "attempt_limit", "postcondition_failed",
    "evidence_changed", "unsupported_extension",
)]
MAX_ATTEMPTS = 5


class ProjectGitPolicyAttempt(models.Model):
    _name = "project.git.policy.attempt"
    _inherit = "project.git.policy.task.scope"
    _description = "Git Policy Scheduled Attempt"
    _check_company_auto = True
    _order = "id"

    activation_id = fields.Many2one("project.git.policy.activation", required=True, readonly=True, ondelete="restrict", index=True)
    revision_id = fields.Many2one(related="activation_id.revision_id", store=True, readonly=True)
    rule_id = fields.Many2one(related="activation_id.rule_id", store=True, readonly=True)
    repository_id = fields.Many2one("project.git.repository", required=True, readonly=True, ondelete="restrict", index=True)
    project_id = fields.Many2one("project.project", required=True, readonly=True, ondelete="restrict", index=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True, ondelete="restrict", index=True)
    task_id = fields.Many2one("project.task", required=True, readonly=True, ondelete="restrict", index=True)
    agile_key = fields.Char(required=True, readonly=True, index=True)
    pull_request_id = fields.Many2one("project.git.pull.request", required=True, readonly=True, ondelete="restrict", index=True)
    provider_request_id = fields.Char(required=True, readonly=True, index=True)
    expected_stage_id = fields.Many2one("project.task.type", required=True, readonly=True, ondelete="restrict")
    expected_transition_version = fields.Integer(required=True, readonly=True)
    observation_id = fields.Many2one("project.git.policy.observation", required=True, readonly=True, ondelete="restrict")
    state = fields.Selection(STATES, required=True, readonly=True, index=True)
    reason = fields.Selection(ATTEMPT_REASONS, required=True, readonly=True)
    attempt_count = fields.Integer(default=0, readonly=True)
    next_retry_at = fields.Datetime(readonly=True, index=True)
    lease_token = fields.Char(readonly=True, groups="base.group_system")
    lease_expires_at = fields.Datetime(readonly=True, index=True)
    event_ids = fields.One2many("project.git.policy.attempt.event", "attempt_id", readonly=True)

    _candidate_unique = models.Constraint(
        "UNIQUE(activation_id, repository_id, provider_request_id, agile_key)",
        "This approval/PR/Task candidate is already retained.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(_("Only the bounded private scheduler can create an attempt."))

    def write(self, values):
        raise AccessError(_("Scheduling state is private; retry cannot widen an attempt."))

    def unlink(self):
        raise ValidationError(_("Attempt history is retained."))

    def _set_schedule(self, values):
        """Only fixed scheduling fields; immutable candidate fields never change."""
        allowed = {"state", "reason", "attempt_count", "next_retry_at", "lease_token", "lease_expires_at"}
        if set(values) - allowed:
            raise ValidationError(_("Scheduling updates cannot alter candidate identity."))
        return super(ProjectGitPolicyAttempt, self.sudo().with_context({})).write(values)

    @api.model
    def _enqueue(self, activation, pr, task, observation, result):
        """Producer already locked/revalidated scope and sealed current evidence."""
        domain = [("activation_id", "=", activation.id), ("repository_id", "=", pr.repository_id.id),
                  ("provider_request_id", "=", pr.provider_request_id), ("agile_key", "=", task.agile_key)]
        existing = self.search(domain, limit=1)
        if existing:
            return existing
        state = {"matched": "queued", "waiting": "waiting", "conflicted": "rejected"}[result[0]]
        attempt = super(ProjectGitPolicyAttempt, self.sudo().with_context({})).create({
            "activation_id": activation.id, "repository_id": pr.repository_id.id,
            "project_id": activation.project_id.id, "company_id": activation.company_id.id,
            "task_id": task.id, "agile_key": task.agile_key, "pull_request_id": pr.id,
            "provider_request_id": pr.provider_request_id, "expected_stage_id": task.stage_id.id,
            "expected_transition_version": task.git_policy_transition_version,
            "observation_id": observation.id, "state": state, "reason": result[1],
            "next_retry_at": fields.Datetime.now() + timedelta(seconds=60) if state == "waiting" else False,
        })
        attempt._append_event(state, result[1])
        return attempt

    def _append_event(self, state, reason):
        self.ensure_one()
        return self.env["project.git.policy.attempt.event"]._append(self, state, reason)

    def _settle(self, state, reason):
        self.ensure_one()
        retry = fields.Datetime.now() + timedelta(seconds=min(3600, 60 * 2 ** max(0, self.attempt_count - 1)))
        self._set_schedule({"state": state, "reason": reason, "lease_token": False, "lease_expires_at": False,
                            "next_retry_at": retry if state in {"waiting", "retryable"} else False})
        self._append_event(state, reason)

    @api.model
    def _try_lock(self, records):
        """Fixed internal control models, nonblocking and ordered before attempt locks."""
        if not records:
            return False
        records.flush_recordset()
        self.env.cr.execute(SQL("SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE SKIP LOCKED",
                                SQL.identifier(records._table), tuple(records.ids)))
        rows = self.env.cr.fetchall()
        records.invalidate_recordset()
        return len(rows) == len(records)

    @api.model
    def _claim_attempt(self):
        """Claims serialize on control rows before attempts; lease is not permission."""
        now = fields.Datetime.now()
        service = self.sudo().with_context({})
        candidates = service.search([
            "|", "&", ("state", "in", ["queued", "waiting", "retryable"]),
            "|", ("next_retry_at", "=", False), ("next_retry_at", "<=", now),
            "&", ("state", "=", "processing"), ("lease_expires_at", "<=", now),
        ], order="id", limit=MAX_BATCH)
        for candidate in candidates:
            controls = (candidate.project_id, candidate.repository_id, candidate.rule_id, candidate.activation_id, candidate)
            if not all(service._try_lock(rows) for rows in controls):
                continue
            if not candidate._eligible(now):
                continue
            if candidate.attempt_count >= MAX_ATTEMPTS:
                candidate._settle("failed", "attempt_limit")
                continue
            candidate._set_schedule({
                "state": "processing", "attempt_count": candidate.attempt_count + 1,
                "lease_token": secrets.token_urlsafe(24), "lease_expires_at": now + timedelta(minutes=5),
                "next_retry_at": False,
            })
            return candidate
        return service.browse()

    def _eligible(self, now):
        self.ensure_one()
        if self.state == "processing":
            return bool(self.lease_expires_at and self.lease_expires_at <= now)
        return self.state in {"queued", "waiting", "retryable"} and (not self.next_retry_at or self.next_retry_at <= now)


class ProjectGitPolicyAttemptEvent(models.Model):
    _name = "project.git.policy.attempt.event"
    _inherit = "project.git.policy.task.scope"
    _description = "Immutable Git Policy Attempt Audit"
    _check_company_auto = True
    _order = "id"

    attempt_id = fields.Many2one("project.git.policy.attempt", required=True, readonly=True, ondelete="restrict", index=True)
    project_id = fields.Many2one(related="attempt_id.project_id", store=True, readonly=True)
    company_id = fields.Many2one(related="attempt_id.company_id", store=True, readonly=True)
    task_id = fields.Many2one(related="attempt_id.task_id", store=True, readonly=True)
    state = fields.Selection(STATES, required=True, readonly=True)
    reason = fields.Selection(ATTEMPT_REASONS, required=True, readonly=True)
    attempt_count = fields.Integer(required=True, readonly=True)
    recorded_at = fields.Datetime(required=True, readonly=True)
    _event_once = models.Constraint("UNIQUE(attempt_id, state, reason, attempt_count)", "This scheduling event is already retained.")

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(_("Only settled attempt processing appends audit events."))

    def write(self, values):
        raise ValidationError(_("Scheduling events are immutable."))

    def unlink(self):
        raise ValidationError(_("Scheduling events are retained."))

    @api.model
    def _append(self, attempt, state, reason):
        domain = [("attempt_id", "=", attempt.id), ("state", "=", state),
                  ("reason", "=", reason), ("attempt_count", "=", attempt.attempt_count)]
        existing = self.sudo().search(domain, limit=1)
        return existing or super(ProjectGitPolicyAttemptEvent, self.sudo().with_context({})).create({
            "attempt_id": attempt.id, "state": state, "reason": reason,
            "attempt_count": attempt.attempt_count, "recorded_at": fields.Datetime.now(),
        })

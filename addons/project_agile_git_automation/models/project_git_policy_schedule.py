"""Native bounded scheduler, independent of receipts and fact normalization."""

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .policy_evidence import MAX_BATCH


class ProjectGitPolicySchedule(models.Model):
    _name = "project.git.policy.schedule"
    _inherit = "project.git.policy.scope"
    _description = "Private Repository Policy Discovery Cursor"

    repository_id = fields.Many2one(
        "project.git.repository", required=True, readonly=True, ondelete="restrict"
    )
    project_id = fields.Many2one(
        related="repository_id.project_id", store=True, readonly=True
    )
    company_id = fields.Many2one(
        related="repository_id.company_id", store=True, readonly=True
    )
    after_pr_id = fields.Integer(default=0, readonly=True)
    next_run_at = fields.Datetime(
        required=True, readonly=True, default=fields.Datetime.now, index=True
    )
    reason = fields.Selection(
        [
            ("scanned", "Scanned"),
            ("evidence_limit", "Evidence Limit"),
            ("inactive_policy", "Inactive Policy"),
            ("invalid_authority", "Invalid Authority"),
        ],
        readonly=True,
    )
    _repository_once = models.Constraint(
        "UNIQUE(repository_id)", "One cursor per stable repository."
    )

    @api.model_create_multi
    # Public callers must not manufacture discovery cursors.
    def create(self, vals_list):  # pylint: disable=method-required-super
        raise AccessError(
            _("Only explicit approved apply activation creates discovery cursors.")
        )

    # Scheduling writes belong exclusively to the private scheduler.
    def write(self, values):  # pylint: disable=method-required-super
        raise AccessError(_("Discovery state is private scheduling data."))

    # Discovery identity is retained rather than deleted.
    def unlink(self):  # pylint: disable=method-required-super
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("Discovery identity is retained."))

    @api.model
    def _ensure(self, activation):
        existing = self.sudo().search(
            [("repository_id", "=", activation.repository_id.id)], limit=1
        )
        return existing or super(
            # Cursor data is server-derived; discard caller defaults.
            ProjectGitPolicySchedule,
            self.sudo().with_context({}),  # pylint: disable=context-overridden
        ).create(
            {
                "repository_id": activation.repository_id.id,
            }
        )

    # Side-effect-only cursor update; the native write result is not its API.
    def _discover_page(self):  # pylint: disable=missing-return
        self.ensure_one()
        now = fields.Datetime.now()
        cursor, reason = self.after_pr_id, "inactive_policy"
        active = (
            self.env["project.git.policy.rule"]
            .sudo()
            .search(
                [
                    ("repository_id", "=", self.repository_id.id),
                    ("activation_id.mode", "=", "apply"),
                ],
                order="id",
                limit=MAX_BATCH + 1,
            )
        )
        if len(active) > MAX_BATCH:
            reason = "evidence_limit"
        elif (
            active
            and self.project_id.git_policy_enabled
            and self.project_id.git_policy_mode == "apply"
        ):
            # Cursor authority comes from an approved persisted owner, not the cron
            # identity or user/company/model values in a receipt or RPC context.
            # Replace cron/caller authority with the persisted owner's company.
            # pylint: disable-next=context-overridden
            repository = self.repository_id.with_user(active[0].owner_id).with_context(
                {"allowed_company_ids": self.company_id.ids}
            )
            try:
                _, next_id, diagnostic = repository.env[
                    "project.git.policy.attempt"
                ]._discover_repository(repository, cursor)
                cursor = next_id if next_id != cursor else 0
                reason = (
                    "evidence_limit" if diagnostic == "evidence_limit" else "scanned"
                )
            except (AccessError, ValidationError):
                reason = "invalid_authority"
        # Exclude caller defaults from private cursor progress writes.
        # pylint: disable-next=context-overridden
        super(ProjectGitPolicySchedule, self.sudo().with_context({})).write(
            {
                "after_pr_id": cursor,
                "reason": reason,
                "next_run_at": now + timedelta(seconds=60),
            }
        )

    @api.model
    def _cron_process_git_policy(self):
        """Commit progress only in an actual native cron after each settled
        savepoint.
        """
        cron = self.env.ref("project_agile_git_automation.ir_cron_git_policy")
        progress = (
            self.env["ir.cron.progress"]
            .sudo()
            .browse(self.env.context.get("ir_cron_progress_id"))
            .exists()
        )
        if (
            not progress
            or progress.cron_id != cron
            or self.env.context.get("cron_id") != cron.id
        ):
            raise AccessError(
                _("Policy progress commits belong to the native scheduler only.")
            )
        # Preserve the native cron progress context exactly, without merging.
        # pylint: disable-next=context-overridden
        service = self.sudo().with_context(self.env.context)
        pages = service.search(
            [("next_run_at", "<=", fields.Datetime.now())],
            order="next_run_at, id",
            limit=1,
        )
        pages = pages.try_lock_for_update(limit=1)
        if pages:
            with self.env.cr.savepoint():
                pages._discover_page()
            if not self.env["ir.cron"]._commit_progress(1, remaining=0):
                return
        # The loop index is intentionally unused; MAX_BATCH bounds claims.
        for item_index in range(MAX_BATCH):  # noqa: B007
            with self.env.cr.savepoint():
                attempt = service.env["project.git.policy.attempt"]._claim_attempt()
                if not attempt:
                    break
                attempt._process_claim()
            if not self.env["ir.cron"]._commit_progress(1, remaining=0):
                break


class ProjectGitPolicyActivation(models.Model):
    _inherit = "project.git.policy.activation"

    @api.model
    def _create_approved(self, revision, timestamp):
        activation = super()._create_approved(revision, timestamp)
        if activation.mode == "apply":
            self.env["project.git.policy.schedule"]._ensure(activation)
        return activation

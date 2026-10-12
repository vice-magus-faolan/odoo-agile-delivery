"""Immutable two-person approval epochs and append-only revocation tombstones."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .policy_authority import (
    MODES,
    check_identity,
    check_scope,
    check_task_authority,
    lock_records,
    stage_fingerprint,
)
from .policy_authority_profile import check_supported_profile

REASONS = [
    (name, name.replace("_", " ").title())
    for name in (
        "disabled",
        "replaced",
        "rule_changed",
        "revision_changed",
        "owner_changed",
        "archived",
        "project_changed",
        "repository_changed",
        "stage_changed",
        "identity_changed",
        "security_changed",
        "authority_changed",
    )
]


class ProjectGitPolicyActivation(models.Model):
    _name = "project.git.policy.activation"
    _inherit = "project.git.policy.scope"
    _description = "Git Policy Approval Epoch"
    _check_company_auto = True
    _order = "activated_at desc, id desc"

    revision_id = fields.Many2one(
        "project.git.policy.revision",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    rule_id = fields.Many2one(related="revision_id.rule_id", store=True, readonly=True)
    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    project_id = fields.Many2one(
        "project.project", required=True, readonly=True, ondelete="restrict", index=True
    )
    company_id = fields.Many2one(
        "res.company", required=True, readonly=True, ondelete="restrict", index=True
    )
    owner_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict"
    )
    approver_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict"
    )
    execution_user_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict"
    )
    activated_at = fields.Datetime(required=True, readonly=True)
    mode = fields.Selection(MODES, required=True, readonly=True)
    authority_epoch = fields.Integer(required=True, readonly=True)
    project_authority_epoch = fields.Integer(required=True, readonly=True)
    stage_fingerprint = fields.Char(required=True, readonly=True)
    native_side_effects_acknowledged = fields.Boolean(required=True, readonly=True)
    revocation_ids = fields.One2many(
        "project.git.policy.revocation", "activation_id", readonly=True
    )

    _revision_once = models.Constraint(
        "UNIQUE(revision_id)",
        "A revision can receive only one immutable approval epoch.",
    )

    @api.model_create_multi
    # Public creation must reject; only the authorized private producer persists.
    def create(self, vals_list):  # pylint: disable=method-required-super
        raise AccessError(
            _("Activation records require the explicit authorized activation action.")
        )

    # Approval snapshots are immutable; delegation would permit mutation.
    def write(self, values):  # pylint: disable=method-required-super
        raise ValidationError(_("Policy activation snapshots are immutable."))

    # Retained approval evidence cannot be deleted.
    def unlink(self):  # pylint: disable=method-required-super
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("Policy activation history is retained."))

    @api.model
    def _create_approved(self, revision, timestamp):
        """Persist only server-derived values after the public action's
        authority check.
        """
        if revision.approver_id != self.env.user or not revision.approved_at:
            raise AccessError(_("A current explicit approval is required."))
        values = {
            "revision_id": revision.id,
            "repository_id": revision.repository_id.id,
            "project_id": revision.project_id.id,
            "company_id": revision.company_id.id,
            "owner_id": revision.owner_id.id,
            "approver_id": revision.approver_id.id,
            "execution_user_id": revision.execution_user_id.id,
            "activated_at": timestamp,
            "mode": revision.project_id.git_policy_mode,
            "authority_epoch": revision.rule_id.authority_epoch,
            "project_authority_epoch": revision.project_id.git_policy_authority_epoch,
            "stage_fingerprint": stage_fingerprint(revision),
            "native_side_effects_acknowledged": True,
        }
        # Remove all caller defaults before the authorized snapshot write.
        # pylint: disable-next=context-overridden
        return super(ProjectGitPolicyActivation, self.sudo().with_context({})).create(
            values
        )

    def _revoke(self, reason):
        """Terminal idempotent revocation.

        No activation can be resurrected by restoring access.
        """
        self.rule_id._lock_control()
        lock_records(self)
        for activation in self:
            if not activation.revocation_ids:
                self.env["project.git.policy.revocation"]._append(activation, reason)
            if activation.rule_id.activation_id == activation:
                activation.rule_id._set_activation(False)

    def _check_current_authority(self, task=None):
        self.ensure_one()
        rule, project = self.rule_id, self.project_id
        if self.revocation_ids or rule.activation_id != self or not rule.active:
            raise ValidationError(_("Approval epoch is no longer current."))
        if not project.git_policy_enabled or project.git_policy_mode != self.mode:
            raise ValidationError(_("Project has disabled or changed policy mode."))
        if (
            self.authority_epoch != rule.authority_epoch
            or self.project_authority_epoch != project.git_policy_authority_epoch
        ):
            raise ValidationError(_("Policy authority epoch has changed."))
        if rule.owner_id != self.owner_id or self.owner_id == self.approver_id:
            raise ValidationError(_("Policy approval ownership has changed."))
        check_scope(self.repository_id, self.project_id, self.company_id)
        for user in (self.owner_id, self.approver_id):
            check_identity(user, self.repository_id, manager=True)
        check_supported_profile(
            self.repository_id,
            self.owner_id | self.approver_id | self.execution_user_id,
        )
        for user in (self.owner_id, self.approver_id):
            check_task_authority(user, self.repository_id, task)
        check_task_authority(self.execution_user_id, self.repository_id, task)
        if stage_fingerprint(self.revision_id) != self.stage_fingerprint:
            raise ValidationError(_("Approved stage configuration has changed."))

    def _validate_current_authority(self, task=None):
        """Private fail-closed validation for future evaluator/apply.

        Never a Task write.

        Revocation persists only if the enclosing caller commits its transaction.
        Future workers must lock in ADR-012 order and re-read before using this.
        An explicit concrete Task repeats record-level checks at the apply boundary.
        """
        self.ensure_one()
        self.rule_id._lock_control()
        lock_records(self)
        try:
            self._check_current_authority(task)
        except (AccessError, ValidationError):
            self._revoke("authority_changed")
            return False
        return True

    @api.model
    def _revoke_matching(self, domain, reason):
        """Revoke-only hook after native authorization.

        No existence results leave this method.
        """
        activations = self.sudo().search(domain + [("revocation_ids", "=", False)])
        activations._revoke(reason)


class ProjectGitPolicyRevocation(models.Model):
    _name = "project.git.policy.revocation"
    _inherit = "project.git.policy.scope"
    _description = "Git Policy Revocation Tombstone"
    _check_company_auto = True

    activation_id = fields.Many2one(
        "project.git.policy.activation",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    project_id = fields.Many2one(
        related="activation_id.project_id", store=True, readonly=True
    )
    company_id = fields.Many2one(
        related="activation_id.company_id", store=True, readonly=True
    )
    revoked_at = fields.Datetime(required=True, readonly=True)
    reason = fields.Selection(REASONS, required=True, readonly=True)

    _activation_once = models.Constraint(
        "UNIQUE(activation_id)", "Approval epochs have one terminal revocation."
    )

    @api.model_create_multi
    # Only the private revocation producer may create a tombstone.
    def create(self, vals_list):  # pylint: disable=method-required-super
        raise AccessError(
            _(
                "Revocations require an authorized control action "
                "or native revocation hook."
            )
        )

    # Tombstones remain immutable; super would change history.
    def write(self, values):  # pylint: disable=method-required-super
        raise ValidationError(_("Policy revocations are append-only."))

    # Deletion would allow a revoked epoch to lose its terminal evidence.
    def unlink(self):  # pylint: disable=method-required-super
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("Policy revocations are retained."))

    @api.model
    def _append(self, activation, reason):
        # Drop caller defaults before persisting server-derived revocation data.
        # pylint: disable-next=context-overridden
        return super(ProjectGitPolicyRevocation, self.sudo().with_context({})).create(
            {
                "activation_id": activation.id,
                "reason": reason,
                "revoked_at": fields.Datetime.now(),
            }
        )

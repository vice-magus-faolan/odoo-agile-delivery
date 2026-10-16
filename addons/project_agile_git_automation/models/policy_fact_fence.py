"""Optional observation fencing, never policy evaluation or workflow mutation.

Provenance mutations advance a repository input version through the ORM. Actual
approvals and effects publish their latest immutable record on that same row, so
a concurrent input edit cannot commit alongside stale policy authority/evidence.
Rolled-back operations roll back both writes. Core facts remain independent.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .policy_revocation_hooks import _policy_ready


class ProjectGitRepository(models.Model):
    _inherit = "project.git.repository"

    git_policy_evidence_version = fields.Integer(
        default=0, readonly=True, copy=False, groups="base.group_system"
    )

    git_policy_last_activation_id = fields.Many2one(
        "project.git.policy.activation",
        readonly=True,
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help=(
            "Private approval publication marker creating an ORM shared-row conflict "
            "with competing repository authority/evidence changes. Not authorization, "
            "a lease counter or a recovery/navigation feature."
        ),
    )
    git_policy_last_effect_id = fields.Many2one(
        "project.git.policy.effect",
        readonly=True,
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help=(
            "Private effect publication marker creating an ORM shared-row conflict "
            "with competing repository authority/evidence changes. Not authorization, "
            "a lease counter or a recovery/navigation feature."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        protected = {
            "git_policy_evidence_version",
            "git_policy_last_activation_id",
            "git_policy_last_effect_id",
        }
        if any(protected.intersection(values) for values in vals_list):
            raise ValidationError(
                _("Repository policy evidence and activity are server-owned.")
            )
        context = {
            key: value
            for key, value in self.env.context.items()
            if key.removeprefix("default_") not in protected
        }
        # Replace context to remove only defaults for server-owned policy fields.
        scoped = self.with_env(self.env(context=context))
        return super(ProjectGitRepository, scoped).create(vals_list)

    def write(self, values):
        if {
            "git_policy_evidence_version",
            "git_policy_last_activation_id",
            "git_policy_last_effect_id",
        }.intersection(values):
            raise ValidationError(
                _("Repository policy evidence and activity are server-owned.")
            )
        return super().write(values)

    def _git_policy_advance_evidence(self):
        """Called only after input ACL checks; rollback includes the input mutation."""
        for repository in self:
            version = repository.git_policy_evidence_version + 1
            super(ProjectGitRepository, repository.sudo()).write(
                {"git_policy_evidence_version": version}
            )

        return True

    def _git_policy_record_activation(self, activation):
        """Publish approval to conflict with repository authority/evidence edits."""
        self.ensure_one()
        if activation.repository_id != self:
            raise ValidationError(_("Policy approval must retain its repository."))
        return super(ProjectGitRepository, self.sudo()).write(
            {
                "git_policy_last_activation_id": activation.id,
            }
        )

    def _git_policy_record_effect(self, effect):
        """Publish effect for an ORM conflict with repository authority/input edits."""
        self.ensure_one()
        if effect.repository_id != self:
            raise ValidationError(_("Policy effect must retain its repository."))
        return super(ProjectGitRepository, self.sudo()).write(
            {
                "git_policy_last_effect_id": effect.id,
            }
        )


def fence_inputs(records, vals_list=()):
    """Internal fixed repository mapping; native ACLs/validation remain
    authoritative.
    """
    if not _policy_ready(records.env):
        return
    ids = records.sudo().repository_id.ids
    ids += [
        v["repository_id"] for v in vals_list if type(v.get("repository_id")) is int
    ]
    repositories = (
        records.env["project.git.repository"].sudo().browse(sorted(set(ids))).exists()
    )
    repositories._git_policy_advance_evidence()


class PolicyEvidenceFence(models.AbstractModel):
    _name = "project.git.policy.evidence.fence"
    _description = "Private Optional Provenance Input Fence"

    @api.model_create_multi
    def create(self, vals_list):
        self.check_access("create")
        fence_inputs(self, vals_list)
        return super().create(vals_list)

    def _policy_requires_evidence_fence(self, values):
        """Serialize provenance writes unless a model proves they cannot be evidence."""
        return True

    def write(self, values):
        self.check_access("write")
        if self._policy_requires_evidence_fence(values):
            fence_inputs(self, [values])
        return super().write(values)

    def unlink(self):
        self.check_access("unlink")
        fence_inputs(self)
        return super().unlink()


class ProjectGitPullRequest(models.Model):
    _name = "project.git.pull.request"
    _inherit = ["project.git.pull.request", "project.git.policy.evidence.fence"]


class ProjectGitCheck(models.Model):
    _name = "project.git.check"
    _inherit = ["project.git.check", "project.git.policy.evidence.fence"]


class ProjectGitDelivery(models.Model):
    _name = "project.git.delivery"
    _inherit = ["project.git.delivery", "project.git.policy.evidence.fence"]

    def _policy_requires_evidence_fence(self, values):
        """Lease bookkeeping cannot qualify an unprocessed delivery as evidence."""
        unsettled_states = {"queued", "retryable", "processing"}
        lease_fields = {
            "state",
            "lease_token",
            "lease_expires_at",
            "attempt_count",
            "next_retry_at",
        }
        # Keep the complete recordset fenced for mixed/protected input. A later
        # settlement or provenance edit still conflicts with policy application;
        # leasing distinct queued rows must not acquire their shared parent lock.
        if (
            values
            and set(values) <= lease_fields
            and ("state" not in values or values["state"] in unsettled_states)
            and all(
                delivery.state in unsettled_states and not delivery.processed_at
                for delivery in self
            )
        ):
            return False
        return super()._policy_requires_evidence_fence(values)


class ProjectGitAssociationAudit(models.Model):
    _name = "project.git.association.audit"
    _inherit = ["project.git.association.audit", "project.git.policy.evidence.fence"]


class ProjectGitTaskAssociation(models.Model):
    _name = "project.git.task.association"
    _inherit = ["project.git.task.association", "project.git.policy.evidence.fence"]

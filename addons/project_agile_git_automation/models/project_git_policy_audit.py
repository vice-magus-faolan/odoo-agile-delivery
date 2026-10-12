"""Inert, append-only contract fixture; no policy evaluator or effect producer."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ProjectGitPolicyAudit(models.Model):
    """A bounded synthetic fixture receipt, never evidence of an applied effect.

    There is no production producer in this skeleton. Trusted internal code may
    create fixture rows in superuser mode; context cannot grant that authority.
    This is not an authenticated observation seal or an apply marker.
    """

    _name = "project.git.policy.audit"
    _description = "Git Policy Contract Audit"
    _check_company_auto = True
    _order = "observed_at desc, id desc"

    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    delivery_id = fields.Many2one(
        "project.git.delivery",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="repository_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    mode = fields.Selection(
        [("dry_run", "Dry Run")],
        required=True,
        default="dry_run",
        readonly=True,
    )
    reason = fields.Selection(
        [("contract_fixture", "Contract Fixture (No Effect)")],
        required=True,
        default="contract_fixture",
        readonly=True,
    )
    observed_at = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Reject user/RPC authors, including forged provenance/context flags."""
        if not self.env.is_superuser():
            raise AccessError(
                _("Policy audit records require a trusted internal producer.")
            )
        return super().create(vals_list)

    @api.constrains("repository_id", "delivery_id")
    def _check_fixture_scope(self):
        for audit in self:
            if (
                not audit.company_id
                or audit.delivery_id.repository_id != audit.repository_id
            ):
                raise ValidationError(
                    _("Policy audit provenance must belong to its company repository.")
                )

    # Contract receipts are append-only; delegation would mutate evidence.
    def write(self, values):  # pylint: disable=method-required-super
        raise ValidationError(_("Policy audit records are append-only."))

    # Contract receipts are retained evidence, not disposable model records.
    def unlink(self):  # pylint: disable=method-required-super
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("Policy audit records are append-only."))

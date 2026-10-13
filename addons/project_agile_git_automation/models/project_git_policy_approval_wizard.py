"""Explicit native-effects acknowledgment; no identity or action comes from context."""

from odoo import api, fields, models

from .policy_authority import clean_context, reject_keys, require_capability


# Preserve the existing native approval boundary and module import layout.
# pylint: disable-next=no-wizard-in-models
class ProjectGitPolicyApprovalWizard(models.TransientModel):
    _name = "project.git.policy.approval.wizard"
    _description = "Approve Git Policy Revision"

    revision_id = fields.Many2one(
        "project.git.policy.revision", required=True, readonly=True
    )
    acknowledge_native_side_effects = fields.Boolean(default=False)

    @api.model_create_multi
    def create(self, vals_list):
        require_capability(self.env)
        for values in vals_list:
            reject_keys(values, {"revision_id", "acknowledge_native_side_effects"})
            revision = self.env["project.git.policy.revision"].browse(
                values.get("revision_id")
            )
            revision.check_access("read")
            revision.rule_id._check_control()
        values_list = [
            {**values, "acknowledge_native_side_effects": False} for values in vals_list
        ]
        return super(
            # Replacement discards forged acknowledgment/identity defaults.
            ProjectGitPolicyApprovalWizard,
            self.with_context(clean_context(self.env)),  # pylint: disable=context-overridden
        ).create(values_list)

    def write(self, values):
        require_capability(self.env)
        reject_keys(values, {"acknowledge_native_side_effects"})
        return super().write(values)

    def action_approve(self):
        self.ensure_one()
        self.check_access("write")
        self.revision_id.action_activate(
            acknowledge_native_side_effects=self.acknowledge_native_side_effects
        )
        return {"type": "ir.actions.act_window_close"}

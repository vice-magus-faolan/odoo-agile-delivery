"""Native explicit return reason and template selection; never context authority."""

from odoo import _, fields, models
from odoo.exceptions import ValidationError


# Preserve existing native wizard imports/layout during tooling-only adoption.
# pylint: disable-next=no-wizard-in-models
class SolutionRevisionWizard(models.TransientModel):
    _name = "project.agile.solution.revision.wizard"
    _description = "Explicit Solution Revision Operation"

    revision_id = fields.Many2one(
        "project.agile.solution.revision", required=True, ondelete="cascade"
    )
    operation = fields.Selection(
        [("return", "Return Review to Draft"), ("template", "Copy Template Sections")],
        required=True,
    )
    reason = fields.Text()
    template_id = fields.Many2one("project.agile.solution.template")

    def action_confirm(self):
        self.ensure_one()
        caller = self.sudo(False)
        caller.check_access("write")
        revision = caller.revision_id.exists()
        if not revision:
            raise ValidationError(_("Select an available revision."))
        if self.operation == "return":
            revision.action_return_to_draft(self.reason)
        else:
            revision.action_apply_template(self.template_id.id)
        return {"type": "ir.actions.act_window_close"}

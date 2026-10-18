from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# Preserve existing imports/layout; this tooling change does not move wizards.
# pylint: disable-next=no-wizard-in-models
class ProjectSprintCloseWizard(models.TransientModel):
    _name = "project.sprint.close.wizard"
    _description = "Close Sprint"

    sprint_id = fields.Many2one(
        "project.sprint", required=True, readonly=True, ondelete="cascade"
    )
    project_id = fields.Many2one(related="sprint_id.project_id", readonly=True)
    company_id = fields.Many2one(related="sprint_id.company_id", readonly=True)
    team_id = fields.Many2one(related="sprint_id.team_id", readonly=True)
    unfinished_task_count = fields.Integer(compute="_compute_unfinished_task_count")
    unfinished_disposition = fields.Selection(
        [
            ("product_backlog", "Move to Product Backlog"),
            ("draft_sprint", "Move to Draft Sprint"),
        ],
        required=True,
        default="product_backlog",
    )
    target_sprint_id = fields.Many2one(
        "project.sprint", string="Draft Sprint", ondelete="restrict"
    )

    @api.depends("sprint_id")
    def _compute_unfinished_task_count(self):
        for wizard in self:
            wizard.unfinished_task_count = (
                self.env["project.task"]
                .with_context(active_test=False)
                .search_count(
                    [("sprint_id", "=", wizard.sprint_id.id), ("state", "!=", "1_done")]
                )
            )

    @api.constrains("unfinished_disposition", "target_sprint_id")
    def _check_target_choice(self):
        for wizard in self:
            if (
                wizard.unfinished_disposition == "draft_sprint"
                and not wizard.target_sprint_id
            ):
                raise ValidationError(_("Select a draft Sprint for carry-over."))
            if (
                wizard.unfinished_disposition == "product_backlog"
                and wizard.target_sprint_id
            ):
                raise ValidationError(
                    _("Product Backlog disposition cannot select a target Sprint.")
                )

    def action_confirm(self):
        self.ensure_one()
        return self.sprint_id._close_with_disposition(
            self.unfinished_disposition, self.target_sprint_id
        )

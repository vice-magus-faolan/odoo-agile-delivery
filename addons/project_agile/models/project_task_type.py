from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    agile_item_type_ids = fields.Many2many(
        "project.agile.item.type",
        string="Agile Item Types",
        help=(
            "Empty allows all item types. Non-Agile and untyped tasks "
            "remain unrestricted."
        ),
    )

    @api.constrains("agile_item_type_ids", "project_ids")
    def _check_agile_stage_policy(self):
        tasks = (
            self.env["project.task"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [("stage_id", "in", self.ids), ("project_id.agile_enabled", "=", True)]
            )
        )
        try:
            tasks._check_agile_stage()
        except ValidationError as error:
            raise ValidationError(
                _(
                    "This stage policy would invalidate existing Agile work. "
                    "Move that work first."
                )
            ) from error

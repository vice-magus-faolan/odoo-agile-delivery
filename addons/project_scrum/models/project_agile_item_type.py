from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectAgileItemType(models.Model):
    _inherit = "project.agile.item.type"

    can_schedule_in_sprint = fields.Boolean(default=True)

    @api.constrains("can_schedule_in_sprint")
    def _check_scheduled_tasks_remain_eligible(self):
        task_model = self.env["project.task"]
        for item_type in self.filtered(lambda record: not record.can_schedule_in_sprint):
            if task_model.search_count(
                [("agile_item_type_id", "=", item_type.id), ("sprint_id", "!=", False)]
            ):
                raise ValidationError(
                    _("An item type assigned to a Sprint must remain Sprint-eligible.")
                )

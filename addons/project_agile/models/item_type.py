from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectAgileItemType(models.Model):
    _name = "project.agile.item.type"
    _description = "Agile Item Type"
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    uses_story_points = fields.Boolean(default=True)
    allowed_child_type_ids = fields.Many2many(
        "project.agile.item.type",
        "project_agile_item_type_child_rel",
        "parent_type_id",
        "child_type_id",
        string="Allowed Child Item Types",
    )

    _agile_item_type_code_unique = models.Constraint(
        "UNIQUE(code)",
        "The Agile item type code must be unique.",
    )

    @api.constrains("allowed_child_type_ids")
    def _check_allowed_child_reconfiguration(self):
        task_model = self.env["project.task"]
        for item_type in self:
            tasks = task_model.search(
                [
                    ("project_id.agile_enabled", "=", True),
                    ("parent_id", "!=", False),
                    "|",
                    ("agile_item_type_id", "=", item_type.id),
                    ("parent_id.agile_item_type_id", "=", item_type.id),
                ]
            )
            for task in tasks:
                try:
                    task._check_agile_parent_policy()
                except ValidationError as error:
                    raise ValidationError(
                        _(
                            "This item type policy would invalidate existing "
                            "Agile task hierarchy: %(error)s",
                            error=error,
                        )
                    ) from error

    @api.constrains("uses_story_points")
    def _check_point_policy(self):
        # Configuration must not invalidate hidden or archived client work.
        tasks = (
            self.env["project.task"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [("agile_item_type_id", "in", self.filtered("uses_story_points").ids)]
            )
        )
        tasks._check_agile_story_points()

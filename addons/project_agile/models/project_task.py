from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_FIBONACCI_STORY_POINTS = {0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89}


class ProjectTask(models.Model):
    _inherit = "project.task"

    agile_project_enabled = fields.Boolean(
        related="project_id.agile_enabled",
        string="Agile Project Enabled",
        readonly=True,
    )
    # Preserve explicit source labels/translation keys, not an implicit fallback.
    # pylint: disable-next=attribute-string-redundant
    agile_item_type_id = fields.Many2one(
        "project.agile.item.type", string="Agile Item Type", ondelete="restrict"
    )
    # pylint: disable-next=attribute-string-redundant
    agile_key = fields.Char(string="Agile Key", copy=False, readonly=True, index=True)
    agile_story_points = fields.Float(string="Story Points")
    agile_acceptance_criteria = fields.Html(string="Acceptance Criteria")
    # Preserve the existing explicit field label.
    # pylint: disable-next=attribute-string-redundant
    agile_backlog_sequence = fields.Integer(
        string="Agile Backlog Sequence", default=10, index=True
    )

    _agile_task_key_unique = models.Constraint(
        "UNIQUE(agile_key)",
        "The Agile task key must be unique.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        values_list = [dict(values) for values in vals_list]
        project_ids = [
            values.get("project_id")
            for values in values_list
            if values.get("project_id")
        ]
        projects_by_id = {
            project.id: project
            for project in self.env["project.project"].browse(project_ids)
        }
        for values in values_list:
            project = projects_by_id.get(values.get("project_id"))
            if project and project.agile_enabled:
                values["agile_key"] = project._next_agile_task_key()
                if (
                    not values.get("agile_item_type_id")
                    and project.agile_default_item_type_id.active
                ):
                    values["agile_item_type_id"] = project.agile_default_item_type_id.id
            else:
                values.pop("agile_key", None)
        return super().create(values_list)

    def write(self, values):
        if "agile_key" in values:
            for task in self:
                if values["agile_key"] != task.agile_key:
                    raise ValidationError(_("An assigned Agile key is immutable."))
        if "project_id" in values:
            for task in self:
                if task.agile_key and values["project_id"] != task.project_id.id:
                    raise ValidationError(
                        _(
                            "A keyed Agile task cannot move to another project. "
                            "Copy it into the target project instead."
                        )
                    )
        return super().write(values)

    @api.constrains("parent_id", "project_id", "agile_item_type_id")
    def _check_agile_parent_policy(self):
        for task in self:
            parent = task.parent_id
            if not parent:
                continue
            if (
                task.project_id.agile_enabled or parent.project_id.agile_enabled
            ) and task.project_id != parent.project_id:
                raise ValidationError(_("Agile task hierarchies cannot span projects."))
            if not (
                task.project_id.agile_enabled
                and task.agile_item_type_id
                and parent.agile_item_type_id
            ):
                continue
            if (
                task.agile_item_type_id
                not in parent.agile_item_type_id.allowed_child_type_ids
            ):
                raise ValidationError(
                    _("The parent Agile item type does not allow this child item type.")
                )

    @api.constrains("agile_story_points", "project_id")
    def _check_agile_story_points(self):
        for task in self.filtered(lambda task: task.project_id.agile_enabled):
            method = task.project_id.agile_estimation_method
            if method == "none" and task.agile_story_points:
                raise ValidationError(
                    _("Story points require a configured estimation method.")
                )
            if (
                method == "fibonacci"
                and task.agile_story_points not in _FIBONACCI_STORY_POINTS
            ):
                raise ValidationError(
                    _("Story points must use the configured Fibonacci values.")
                )

"""Native milestone navigation for Agile release contents."""

from odoo import fields, models


class ProjectMilestone(models.Model):
    _inherit = "project.milestone"

    agile_project_enabled = fields.Boolean(
        related="project_id.agile_enabled", compute_sudo=False
    )

    def action_view_tasks(self):
        """Keep native navigation outside opted-in Agile milestone Projects."""
        self.ensure_one()
        self.check_access("read")
        project = self.project_id
        project.check_access("read")
        if not (
            project.agile_enabled
            and project.allow_milestones
            and self.env.user.has_group("project.group_project_milestone")
        ):
            return super().action_view_tasks()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "project.action_view_task_from_milestone"
        )
        action.update(
            name=self.env._("Release contents"),
            view_mode="list,kanban,form",
            views=[
                (self.env.ref("project_agile.view_task_list_agile").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            domain=[
                ("milestone_id", "=", self.id),
                ("project_id", "=", project.id),
                ("has_template_ancestor", "=", False),
                ("has_project_template", "=", False),
            ],
            context={
                "default_project_id": project.id,
                "default_milestone_id": self.id,
                "allow_milestones": True,
                "group_by": ["agile_item_type_id", "state"],
            },
        )
        action.pop("res_id", None)
        return action

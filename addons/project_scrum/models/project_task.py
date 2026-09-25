from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    sprint_id = fields.Many2one("project.sprint", string="Sprint", ondelete="set null", index=True)

    @api.constrains("sprint_id", "project_id", "company_id")
    def _check_sprint_assignment(self):
        for task in self.filtered("sprint_id"):
            sprint = task.sprint_id
            if task.project_id != sprint.project_id:
                raise ValidationError(_("A task can only join a Sprint in its own project."))
            if task.company_id != sprint.company_id:
                raise ValidationError(_("A task can only join a Sprint in its own company."))

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks.filtered(lambda record: record.sprint_id.state == "active"):
            task.sprint_id._append_scope_events("added", task)
        return tasks

    def write(self, values):
        if "sprint_id" not in values:
            return super().write(values)
        original_sprints = {task.id: task.sprint_id for task in self}
        result = super().write(values)
        for task in self:
            previous_sprint = original_sprints[task.id]
            current_sprint = task.sprint_id
            if previous_sprint == current_sprint:
                continue
            if previous_sprint.state == "active":
                previous_sprint._append_scope_events("removed", task)
            if current_sprint.state == "active":
                current_sprint._append_scope_events("added", task)
        return result

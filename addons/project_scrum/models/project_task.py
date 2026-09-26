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
            if sprint.state == "closed" and not self.env.is_superuser():
                raise ValidationError(_("Tasks cannot be assigned to a closed Sprint."))

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks.filtered(lambda record: record.sprint_id.state == "active"):
            task.sprint_id._append_scope_events("added", task)
        return tasks

    def write(self, values):
        track_sprint_assignment = "sprint_id" in values
        track_completion = "state" in values
        original_sprints = {task.id: task.sprint_id for task in self} if track_sprint_assignment else {}
        if track_sprint_assignment and not self.env.is_superuser():
            requested_sprint = self.env["project.sprint"].browse(values["sprint_id"]).exists()
            if requested_sprint and requested_sprint.state == "closed":
                raise ValidationError(_("Tasks cannot be assigned to a closed Sprint."))
            if any(sprint.state == "closed" and sprint != requested_sprint for sprint in original_sprints.values()):
                raise ValidationError(_("Tasks cannot be removed from a closed Sprint."))
        original_done_states = {task.id: task.state == "1_done" for task in self} if track_completion else {}
        result = super().write(values)
        if track_sprint_assignment:
            for task in self:
                previous_sprint = original_sprints[task.id]
                current_sprint = task.sprint_id
                if previous_sprint == current_sprint:
                    continue
                if previous_sprint.state == "active":
                    previous_sprint._append_scope_events("removed", task)
                if current_sprint.state == "active":
                    current_sprint._append_scope_events("added", task)
        if track_completion:
            for task in self:
                sprint = task.sprint_id
                was_done = original_done_states[task.id]
                is_done = task.state == "1_done"
                if sprint.state != "active" or was_done == is_done:
                    continue
                sprint._append_scope_events("completed" if is_done else "reopened", task)
        return result

    def _write_sprint_close_assignment(self, target_sprint=False):
        """Move unfinished work without converting close into ordinary scope removal."""
        return super(ProjectTask, self).write(
            {"sprint_id": target_sprint.id if target_sprint else False}
        )

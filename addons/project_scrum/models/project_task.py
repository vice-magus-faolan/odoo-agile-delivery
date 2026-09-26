from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    sprint_id = fields.Many2one("project.sprint", string="Sprint", ondelete="set null", index=True)

    def _validate_sprint_assignment(self, sprint):
        sprint.ensure_one()
        if sprint.state == "closed":
            raise ValidationError(_("Tasks cannot be assigned to a closed Sprint."))
        for task in self:
            if not task.project_id.agile_enabled:
                raise ValidationError(_("Only Agile tasks can be assigned to a Sprint."))
            if task.agile_item_type_id and not task.agile_item_type_id.can_schedule_in_sprint:
                raise ValidationError(_("Only Sprint-eligible Agile tasks can be assigned to a Sprint."))
            if task.project_id != sprint.project_id:
                raise ValidationError(_("A task can only join a Sprint in its own project."))
            if task.company_id != sprint.company_id:
                raise ValidationError(_("A task can only join a Sprint in its own company."))

    def _single_agile_project_for_sprint_action(self):
        self.check_access_rights("write")
        self.check_access_rule("write")
        projects = self.mapped("project_id")
        if len(projects) != 1 or not projects.agile_enabled:
            raise ValidationError(_("Select tasks from one Agile project."))
        return projects

    def action_open_sprint_assignment_wizard(self, operation):
        if operation not in {"assign", "remove"}:
            raise ValidationError(_("Choose a valid Sprint backlog operation."))
        project = self._single_agile_project_for_sprint_action()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assign to Sprint") if operation == "assign" else _("Remove from Sprint"),
            "res_model": "project.sprint.task.assignment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_task_ids": [(6, 0, self.ids)],
                "default_project_id": project.id,
                "default_operation": operation,
            },
        }

    def action_assign_to_sprint(self):
        return self.action_open_sprint_assignment_wizard("assign")

    def action_remove_from_sprint(self):
        return self.action_open_sprint_assignment_wizard("remove")

    @api.constrains("sprint_id", "project_id", "company_id", "agile_item_type_id")
    def _check_sprint_assignment(self):
        for task in self.filtered("sprint_id"):
            task._validate_sprint_assignment(task.sprint_id)

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
        if track_sprint_assignment:
            requested_sprint = self.env["project.sprint"].browse(values["sprint_id"]).exists()
            if requested_sprint:
                self._validate_sprint_assignment(requested_sprint)
            if not self.env.is_superuser() and any(
                sprint.state == "closed" and sprint != requested_sprint
                for sprint in original_sprints.values()
            ):
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

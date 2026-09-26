from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectSprintTaskAssignmentWizard(models.TransientModel):
    _name = "project.sprint.task.assignment.wizard"
    _description = "Assign or Remove Sprint Tasks"

    task_ids = fields.Many2many("project.task", required=True, readonly=True)
    project_id = fields.Many2one("project.project", required=True, readonly=True)
    operation = fields.Selection(
        [("assign", "Assign to Sprint"), ("remove", "Remove from Sprint")],
        required=True,
        readonly=True,
    )
    sprint_id = fields.Many2one("project.sprint", string="Sprint", ondelete="restrict")

    @api.constrains("task_ids", "project_id")
    def _check_tasks_share_project(self):
        for wizard in self:
            if not wizard.task_ids or wizard.task_ids.project_id != wizard.project_id:
                raise ValidationError(_("Select tasks from one Agile project."))

    @api.constrains("operation", "sprint_id")
    def _check_target_choice(self):
        for wizard in self:
            if wizard.operation == "assign" and not wizard.sprint_id:
                raise ValidationError(_("Select a Sprint for assignment."))
            if wizard.operation == "remove" and wizard.sprint_id:
                raise ValidationError(_("Removing tasks must not select a target Sprint."))

    def action_confirm(self):
        self.ensure_one()
        tasks = self.task_ids.exists()
        tasks.check_access("write")
        if self.operation == "assign":
            tasks._validate_sprint_assignment(self.sprint_id)
            if tasks.filtered("sprint_id"):
                raise ValidationError(_("Assign to Sprint only accepts unscheduled Product Backlog tasks."))
            tasks.write({"sprint_id": self.sprint_id.id})
        else:
            if tasks.filtered(lambda task: not task.sprint_id):
                raise ValidationError(_("Remove from Sprint only accepts assigned Sprint Backlog tasks."))
            tasks.write({"sprint_id": False})
        return {"type": "ir.actions.act_window_close"}

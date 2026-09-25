from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ProjectSprintScopeEvent(models.Model):
    """Append-only task-level evidence for Sprint commitment and scope changes."""

    _name = "project.sprint.scope.event"
    _description = "Sprint Scope Event"
    _order = "event_at, id"
    _rec_name = "event_type"

    sprint_id = fields.Many2one("project.sprint", required=True, ondelete="restrict", index=True)
    task_id = fields.Many2one("project.task", required=True, ondelete="restrict", index=True)
    event_type = fields.Selection(
        [("committed", "Committed"), ("added", "Added"), ("removed", "Removed")],
        required=True,
        index=True,
    )
    story_points = fields.Float(required=True)
    actor_id = fields.Many2one("res.users", required=True, readonly=True, ondelete="restrict")
    event_at = fields.Datetime(required=True, readonly=True, index=True)
    reason = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        if not (self.env.is_superuser() or self.env.context.get("project_scrum_allow_event_create")):
            raise AccessError(_("Sprint scope events are created only by Sprint lifecycle actions."))
        return super().create(vals_list)

    def write(self, values):
        if not self.env.is_superuser():
            raise AccessError(_("Sprint scope events are append-only."))
        return super().write(values)

    def unlink(self):
        if not self.env.is_superuser():
            raise AccessError(_("Sprint scope events are append-only."))
        return super().unlink()

    @api.constrains("sprint_id", "task_id")
    def _check_event_task_context(self):
        for event in self:
            if event.task_id.project_id != event.sprint_id.project_id:
                raise ValidationError(_("A Sprint scope event task must belong to the Sprint project."))
            if event.task_id.company_id != event.sprint_id.company_id:
                raise ValidationError(_("A Sprint scope event task must belong to the Sprint company."))

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ProjectSprintScopeEvent(models.Model):
    """Append-only task-level evidence for Sprint commitment and scope changes."""

    _name = "project.sprint.scope.event"
    _description = "Sprint Scope Event"
    _order = "event_at, id"
    _rec_name = "event_type"

    sprint_id = fields.Many2one(
        "project.sprint", required=True, ondelete="restrict", index=True
    )
    task_id = fields.Many2one(
        "project.task", required=True, ondelete="restrict", index=True
    )
    event_type = fields.Selection(
        [
            ("committed", "Committed"),
            ("added", "Added"),
            ("removed", "Removed"),
            ("reestimated", "Reestimated"),
            ("completed", "Completed"),
            ("reopened", "Reopened"),
            ("carried_to_backlog", "Carried to Product Backlog"),
            ("carried_to_sprint", "Carried to Draft Sprint"),
        ],
        required=True,
        index=True,
    )
    story_points = fields.Float(required=True)
    # Preserve the explicit source label/translation key.
    # pylint: disable-next=attribute-string-redundant
    previous_story_points = fields.Float(
        string="Previous Story Points",
        help="The pre-change estimate for a reestimated scope event.",
    )
    actor_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict"
    )
    event_at = fields.Datetime(required=True, readonly=True, index=True)
    reason = fields.Text()
    carryover_target_sprint_id = fields.Many2one(
        "project.sprint", readonly=True, ondelete="restrict", index=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.is_superuser():
            raise AccessError(
                _("Sprint scope events are created only by Sprint lifecycle actions.")
            )
        return super().create(vals_list)

    def write(self, values):
        if not self.env.is_superuser():
            raise AccessError(_("Sprint scope events are append-only."))
        return super().write(values)

    def unlink(self):
        if not self.env.is_superuser():
            # User deletion violates the existing append-only scope contract.
            raise AccessError(  # pylint: disable=no-raise-unlink
                _("Sprint scope events are append-only.")
            )
        return super().unlink()

    @api.constrains("sprint_id", "task_id", "event_type", "carryover_target_sprint_id")
    def _check_event_task_context(self):
        for event in self:
            if (
                event.task_id.project_id != event.sprint_id.project_id
                or event.task_id.company_id != event.sprint_id.company_id
            ):
                raise ValidationError(
                    _(
                        "A Sprint scope event task must belong "
                        "to the Sprint project and company."
                    )
                )
            target = event.carryover_target_sprint_id
            if event.event_type == "carried_to_sprint":
                if (
                    not target
                    or target == event.sprint_id
                    or target.project_id != event.sprint_id.project_id
                    or target.company_id != event.sprint_id.company_id
                    or target.team_id != event.sprint_id.team_id
                ):
                    raise ValidationError(
                        _("Carry-over events require a compatible target Sprint.")
                    )
            elif target:
                raise ValidationError(
                    _("Only carry-over events may reference a target Sprint.")
                )

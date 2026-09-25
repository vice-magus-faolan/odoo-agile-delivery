from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectSprint(models.Model):
    """A team's time-boxed Sprint with an immutable original commitment."""

    _name = "project.sprint"
    _description = "Project Sprint"
    _order = "date_start desc, id desc"

    name = fields.Char(required=True)
    project_id = fields.Many2one("project.project", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="project_id.company_id", store=True, readonly=True, index=True)
    team_id = fields.Many2one("project.agile.team", required=True, ondelete="restrict", index=True)
    date_start = fields.Date()
    date_end = fields.Date()
    goal = fields.Text()
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("closed", "Closed")],
        default="draft",
        required=True,
        copy=False,
        index=True,
    )
    task_ids = fields.One2many("project.task", "sprint_id", string="Tasks")
    committed_task_ids = fields.Many2many(
        "project.task",
        "project_sprint_committed_task_rel",
        "sprint_id",
        "task_id",
        string="Committed Tasks",
        readonly=True,
        copy=False,
    )
    scope_event_ids = fields.One2many("project.sprint.scope.event", "sprint_id", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if any(values.get("state", "draft") != "draft" for values in vals_list):
            raise ValidationError(_("Sprints must be created in draft state."))
        return super().create(vals_list)

    def write(self, values):
        if "state" in values and not self.env.context.get("project_scrum_lifecycle_transition"):
            if any(sprint.state != values["state"] for sprint in self):
                raise ValidationError(_("Use the Sprint lifecycle actions to change state."))
        return super().write(values)

    @api.constrains("project_id", "team_id", "date_start", "date_end")
    def _check_sprint_consistency(self):
        for sprint in self:
            if sprint.project_id and not sprint.project_id.agile_enabled:
                raise ValidationError(_("Sprints require an Agile-enabled project."))
            if sprint.team_id and sprint.team_id.project_id != sprint.project_id:
                raise ValidationError(_("The Agile team must belong to the Sprint project."))
            if sprint.date_start and sprint.date_end and sprint.date_start > sprint.date_end:
                raise ValidationError(_("The Sprint end date cannot precede its start date."))

    @api.constrains("state", "project_id", "team_id")
    def _check_single_active_sprint(self):
        for sprint in self.filtered(lambda record: record.state == "active"):
            duplicate = self.search_count(
                [
                    ("id", "!=", sprint.id),
                    ("state", "=", "active"),
                    ("project_id", "=", sprint.project_id.id),
                    ("team_id", "=", sprint.team_id.id),
                ]
            )
            if duplicate:
                raise ValidationError(_("Only one Sprint can be active for a project and Agile team."))

    def init(self):
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS project_sprint_active_project_team_unique
            ON project_sprint (project_id, team_id)
            WHERE state = 'active'
            """
        )

    def _append_scope_events(self, event_type, tasks, reason=False):
        values = []
        event_at = fields.Datetime.now()
        for task in tasks:
            values.append(
                {
                    "sprint_id": self.id,
                    "task_id": task.id,
                    "event_type": event_type,
                    "story_points": task.agile_story_points,
                    "actor_id": self.env.uid,
                    "event_at": event_at,
                    "reason": reason or False,
                }
            )
        if values:
            self.env["project.sprint.scope.event"].sudo().with_context(
                project_scrum_allow_event_create=True
            ).create(values)

    def action_start(self):
        for sprint in self:
            if sprint.state != "draft":
                raise ValidationError(_("Only a draft Sprint can be started."))
            sprint._check_sprint_consistency()
            if self.search_count(
                [
                    ("state", "=", "active"),
                    ("project_id", "=", sprint.project_id.id),
                    ("team_id", "=", sprint.team_id.id),
                ]
            ):
                raise ValidationError(_("Only one Sprint can be active for a project and Agile team."))
            sprint.committed_task_ids = [fields.Command.set(sprint.task_ids.ids)]
            sprint._append_scope_events("committed", sprint.task_ids)
            sprint.with_context(project_scrum_lifecycle_transition=True).write({"state": "active"})
        return True

    def action_close(self):
        for sprint in self:
            if sprint.state != "active":
                raise ValidationError(_("Only an active Sprint can be closed."))
            sprint.with_context(project_scrum_lifecycle_transition=True).write({"state": "closed"})
        return True

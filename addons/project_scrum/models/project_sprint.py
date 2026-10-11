from psycopg2 import IntegrityError

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectSprint(models.Model):
    """A team time-box with an immutable original commitment."""

    _name = "project.sprint"
    _description = "Project Sprint"
    _order = "date_start desc, id desc"

    # Keep the legacy SQL name: Odoo reuses existing uncommented indexes on
    # upgrade, so populated databases retain enforcement without rebuilding it.
    _active_project_team_unique = models.UniqueIndex(
        "(project_id, team_id) WHERE state = 'active'",
        "Only one Sprint can be active for a project and Agile team.",
    )

    name = fields.Char(required=True)
    project_id = fields.Many2one("project.project", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="project_id.company_id", store=True, readonly=True, index=True)
    team_id = fields.Many2one("project.agile.team", required=True, ondelete="restrict", index=True)
    date_start = fields.Date()
    date_end = fields.Date()
    goal = fields.Text()
    state = fields.Selection([("draft", "Draft"), ("active", "Active"), ("closed", "Closed")], default="draft", required=True, copy=False, index=True)
    closed_at = fields.Datetime(readonly=True, copy=False, index=True)
    task_ids = fields.One2many("project.task", "sprint_id", string="Tasks")
    committed_task_ids = fields.Many2many("project.task", "project_sprint_committed_task_rel", "sprint_id", "task_id", string="Committed Tasks", readonly=True, copy=False)
    scope_event_ids = fields.One2many("project.sprint.scope.event", "sprint_id", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if any(values.get("state", "draft") != "draft" for values in vals_list):
            raise ValidationError(_("Sprints must be created in draft state."))
        return super().create(vals_list)

    def write(self, values):
        if "closed_at" in values and not self.env.is_superuser():
            raise ValidationError(_("Only superuser recovery can correct the close timestamp."))
        if "state" in values and any(sprint.state != values["state"] for sprint in self):
            raise ValidationError(_("Use the Sprint lifecycle actions to change state."))
        if any(sprint.state == "closed" for sprint in self) and values and not self.env.is_superuser():
            raise ValidationError(_("Closed Sprints are immutable. Superuser recovery is explicit administration."))
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

    def _append_scope_events(
        self,
        event_type,
        tasks,
        reason=False,
        carryover_target_sprint=False,
        story_points_by_task=None,
        previous_story_points_by_task=None,
    ):
        event_at = fields.Datetime.now()
        values = [
            {
                "sprint_id": self.id,
                "task_id": task.id,
                "event_type": event_type,
                "story_points": (
                    story_points_by_task.get(task.id, task.agile_story_points)
                    if story_points_by_task
                    else task.agile_story_points
                ),
                "previous_story_points": (
                    previous_story_points_by_task.get(task.id, 0.0)
                    if previous_story_points_by_task
                    else 0.0
                ),
                "actor_id": self.env.uid,
                "event_at": event_at,
                "reason": reason or False,
                "carryover_target_sprint_id": (
                    carryover_target_sprint.id if carryover_target_sprint else False
                ),
            }
            for task in tasks
        ]
        # Return the exact newly created evidence for optional audit extensions;
        # lifecycle values and callers remain unchanged, with no history search.
        return self.env["project.sprint.scope.event"].sudo().create(values)

    def _set_lifecycle_state(self, state):
        values = {"state": state}
        if state == "closed":
            values["closed_at"] = fields.Datetime.now()
        return super(ProjectSprint, self.with_user(SUPERUSER_ID)).write(values)

    def _check_lifecycle_access(self):
        self.check_access("write")

    def _activate(self):
        # Translation can read the user's language. Resolve it before SQL can
        # abort the cursor, without relying on a warm user/context cache.
        active_sprint_message = _("Only one Sprint can be active for a project and Agile team.")
        self.committed_task_ids = [fields.Command.set(self.task_ids.ids)]
        self._append_scope_events("committed", self.task_ids)
        self._append_scope_events(
            "completed", self.task_ids.filtered(lambda task: task.state == "1_done")
        )
        try:
            self._set_lifecycle_state("active")
            self.with_user(SUPERUSER_ID).flush_recordset(["state"])
        except IntegrityError as error:
            # Direct lifecycle calls do not pass through Odoo's RPC error
            # translation; action_start's savepoint rolls back all evidence.
            if error.diag.constraint_name == "project_sprint_active_project_team_unique":
                raise ValidationError(active_sprint_message) from error
            raise

    def action_start(self):
        self._check_lifecycle_access()
        for sprint in self:
            if sprint.state != "draft":
                raise ValidationError(_("Only a draft Sprint can be started."))
            sprint._check_sprint_consistency()
            with self.env.cr.savepoint():
                sprint._activate()
        return True

    def _lock_close_records(self, target_sprint=False):
        sprints = self | target_sprint
        self.env.cr.execute(
            "SELECT id FROM project_sprint WHERE id IN %s ORDER BY id FOR UPDATE",
            [tuple(sorted(sprints.ids))],
        )
        if len(self.env.cr.fetchall()) != len(sprints):
            raise ValidationError(_("A selected Sprint no longer exists."))
        sprints.invalidate_recordset(["state", "project_id", "company_id", "team_id"])

    def _validate_close_target(self, disposition, target_sprint):
        if disposition not in {"product_backlog", "draft_sprint"}:
            raise ValidationError(_("Choose an unfinished-work disposition."))
        if disposition == "product_backlog" and target_sprint:
            raise ValidationError(_("Product Backlog disposition cannot select a target Sprint."))
        if disposition != "draft_sprint":
            return
        if not target_sprint:
            raise ValidationError(_("Select a draft Sprint for carry-over."))
        target_sprint.check_access("read")
        if target_sprint == self or target_sprint.state != "draft" or target_sprint.project_id != self.project_id or target_sprint.company_id != self.company_id or target_sprint.team_id != self.team_id:
            raise ValidationError(_("Carry-over requires a different draft Sprint for the same project, company, and Agile team."))

    def _move_unfinished_tasks(self, tasks, disposition, target_sprint=False):
        tasks.check_access("write")
        tasks._write_sprint_close_assignment(target_sprint)
        event_type = "carried_to_sprint" if target_sprint else "carried_to_backlog"
        self._append_scope_events(event_type, tasks, carryover_target_sprint=target_sprint)

    def _close_with_disposition(self, disposition, target_sprint=False):
        self.ensure_one()
        self._check_lifecycle_access()
        target_sprint = target_sprint.exists() if target_sprint else self.env["project.sprint"]
        with self.env.cr.savepoint():
            self._lock_close_records(target_sprint)
            if self.state != "active":
                raise ValidationError(_("Only an active Sprint can be closed."))
            self._validate_close_target(disposition, target_sprint)
            self.env.cr.execute("SELECT id FROM project_task WHERE sprint_id = %s AND state != %s FOR UPDATE", [self.id, "1_done"])
            unfinished_tasks = self.env["project.task"].browse([row[0] for row in self.env.cr.fetchall()])
            if unfinished_tasks:
                self._move_unfinished_tasks(unfinished_tasks, disposition, target_sprint)
            self._set_lifecycle_state("closed")
        return True

    def _task_backlog_action(self, name, domain):
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "project.task",
            "view_mode": "list,kanban,form",
            "views": [
                (self.env.ref("project_agile.view_task_list_agile_backlog").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            "search_view_id": self.env.ref("project_scrum.view_task_search_scrum").id,
            "domain": domain,
            "context": {"default_project_id": self.project_id.id},
        }

    def action_open_product_backlog(self):
        self.ensure_one()
        return self._task_backlog_action(
            _("Product Backlog"),
            [
                ("project_id", "=", self.project_id.id),
                ("agile_item_type_id.can_schedule_in_sprint", "=", True),
                ("sprint_id", "=", False),
                ("has_template_ancestor", "=", False),
                ("has_project_template", "=", False),
            ],
        )

    def action_open_sprint_backlog(self):
        self.ensure_one()
        return self._task_backlog_action(
            _("Sprint Backlog"),
            [("sprint_id", "=", self.id)],
        )

    def action_close(self):
        self.ensure_one()
        self._check_lifecycle_access()
        if self.state != "active":
            raise ValidationError(_("Only an active Sprint can be closed."))
        if not self.task_ids.filtered(lambda task: task.state != "1_done"):
            return self._close_with_disposition("product_backlog")
        return {"type": "ir.actions.act_window", "name": _("Close Sprint"), "res_model": "project.sprint.close.wizard", "view_mode": "form", "target": "new", "context": {"default_sprint_id": self.id}}

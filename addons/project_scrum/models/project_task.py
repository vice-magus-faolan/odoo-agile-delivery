from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    # Preserve the explicit source label/translation key during tooling adoption.
    # pylint: disable-next=attribute-string-redundant
    sprint_id = fields.Many2one(
        "project.sprint", string="Sprint", ondelete="set null", index=True
    )
    agile_team_id = fields.Many2one(
        "project.agile.team",
        ondelete="restrict",
        index=True,
        help=(
            "Optional backlog ownership. Unteamed work inherits "
            "the assigned Sprint's team."
        ),
    )

    @api.model
    def _product_backlog_domain(self):
        return super()._product_backlog_domain() + [("sprint_id", "=", False)]

    @api.model
    def _sprint_eligible_backlog_domain(self):
        """Narrow the general backlog to work selectable for Sprint planning."""
        return self._product_backlog_domain() + [
            ("agile_item_type_id.can_schedule_in_sprint", "=", True),
        ]

    @api.depends("sprint_id")
    # Compute methods assign fields, not return values.
    # pylint: disable-next=missing-return
    def _compute_agile_is_product_backlog(self):
        super()._compute_agile_is_product_backlog()

    def copy_data(self, default=None):
        default = dict(default or {})
        if self.env.context.get("copy_project"):
            # Native recursion drops root defaults; create children in the destination
            # directly, before Agile hierarchy checks and immutable key assignment.
            project_id = default.get(
                "project_id", self.env.context.get("default_project_id")
            )
            if project_id:
                default["project_id"] = project_id
                self = self.with_context(default_project_id=project_id)
        values_list = super().copy_data(default=default)
        for task, values in zip(self, values_list, strict=False):
            # Project copying also calls this hook for children with narrowed defaults.
            if (
                self.env.context.get("copy_project")
                or values.get("project_id") != task.project_id.id
            ):
                values["agile_team_id"] = default.get("agile_team_id", False)
                values["sprint_id"] = default.get("sprint_id", False)
        return values_list

    @api.model
    def _prepare_sprint_team(self, values, current_teams):
        """Validate the whole requested team set before inheriting one Sprint team."""
        sprint = self.env["project.sprint"].browse(values.get("sprint_id")).exists()
        if not sprint:
            return values
        sprint.check_access("read")
        team = sprint.team_id
        team.check_access("read")
        requested = (
            self.env["project.agile.team"].browse(values["agile_team_id"])
            if "agile_team_id" in values
            else current_teams
        )
        requested.check_access("read")
        if requested - team:
            raise ValidationError(
                self.env._("The task team must match the Sprint team.")
            )
        return dict(values, agile_team_id=team.id)

    @api.constrains("agile_team_id", "sprint_id", "project_id", "company_id")
    def _check_agile_team(self):
        for task in self:
            team = task.agile_team_id
            if not team:
                if task.sprint_id:
                    raise ValidationError(
                        self.env._("Assigned work needs its Sprint team.")
                    )
                continue
            team.check_access("read")
            if (
                not task.project_id.agile_enabled
                or team.project_id != task.project_id
                or team.company_id != task.company_id
            ):
                raise ValidationError(
                    self.env._(
                        "The task team must belong to its Agile Project and company."
                    )
                )
            if task.sprint_id and team != task.sprint_id.team_id:
                raise ValidationError(
                    self.env._("The task team must match the Sprint team.")
                )

    def _validate_sprint_assignment(self, sprint):
        sprint.ensure_one()
        if sprint.state == "closed":
            raise ValidationError(_("Tasks cannot be assigned to a closed Sprint."))
        for task in self:
            if not task.project_id.agile_enabled:
                raise ValidationError(
                    _("Only Agile tasks can be assigned to a Sprint.")
                )
            if (
                not task.agile_item_type_id
                or not task.agile_item_type_id.can_schedule_in_sprint
            ):
                raise ValidationError(
                    _("Only Sprint-eligible Agile tasks can be assigned to a Sprint.")
                )
            if task.project_id != sprint.project_id:
                raise ValidationError(
                    _("A task can only join a Sprint in its own project.")
                )
            if task.company_id != sprint.company_id:
                raise ValidationError(
                    _("A task can only join a Sprint in its own company.")
                )

    def _single_agile_project_for_sprint_action(self):
        self.check_access("write")
        projects = self.mapped("project_id")
        if len(projects) != 1 or not projects.agile_enabled:
            raise ValidationError(_("Select tasks from one Agile project."))
        return projects

    def assign_product_backlog_to_sprint(self, sprint, *, draft_only=False):
        """Assign unscheduled eligible work through the shared Scrum boundary."""
        self.check_access("write")
        sprint = sprint.exists()
        if len(sprint) != 1:
            raise ValidationError(_("Select one available Sprint."))
        sprint.check_access("read")
        if draft_only and sprint.state != "draft":
            raise ValidationError(
                _("Interactive planning can assign work only to a draft Sprint.")
            )
        self._validate_sprint_assignment(sprint)
        if self.filtered("sprint_id"):
            raise ValidationError(
                _("Assign to Sprint only accepts unscheduled Product Backlog tasks.")
            )
        return self.write({"sprint_id": sprint.id})

    def return_sprint_tasks_to_product_backlog(self):
        """Return assigned work through the normal task write and scope-event path."""
        self.check_access("write")
        if self.filtered(lambda task: not task.sprint_id):
            raise ValidationError(
                _("Remove from Sprint only accepts assigned Sprint Backlog tasks.")
            )
        return self.write({"sprint_id": False})

    def action_open_sprint_assignment_wizard(self, operation):
        if operation not in {"assign", "remove"}:
            raise ValidationError(_("Choose a valid Sprint backlog operation."))
        project = self._single_agile_project_for_sprint_action()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assign to Sprint")
            if operation == "assign"
            else _("Remove from Sprint"),
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
        defaults = self.default_get(["sprint_id", "agile_team_id"])
        values_list = [
            self._prepare_sprint_team(
                dict(defaults, **values), self.env["project.agile.team"]
            )
            for values in vals_list
        ]
        tasks = super().create(values_list)
        for task in tasks.filtered(lambda record: record.sprint_id.state == "active"):
            task.sprint_id._append_scope_events("added", task)
            if task.state == "1_done":
                task.sprint_id._append_scope_events("completed", task)
        return tasks

    def _track_active_sprint_assignment_changes(
        self, original_sprints, original_story_points
    ):
        for task in self:
            previous_sprint = original_sprints[task.id]
            current_sprint = task.sprint_id
            if previous_sprint == current_sprint:
                continue
            if previous_sprint.state == "active":
                previous_sprint._append_scope_events(
                    "removed", task, story_points_by_task=original_story_points
                )
            if current_sprint.state == "active":
                current_sprint._append_scope_events("added", task)
                if task.state == "1_done":
                    current_sprint._append_scope_events("completed", task)

    def _track_active_sprint_reestimates(self, original_sprints, original_story_points):
        for task in self:
            sprint = task.sprint_id
            if (
                original_sprints[task.id] == sprint
                and sprint.state == "active"
                and original_story_points[task.id] != task.agile_effective_story_points
            ):
                sprint._append_scope_events(
                    "reestimated",
                    task,
                    previous_story_points_by_task=original_story_points,
                )

    def _track_active_sprint_completion_edges(
        self, original_sprints, original_done_states, track_sprint_assignment
    ):
        for task in self:
            sprint = task.sprint_id
            was_done = original_done_states[task.id]
            is_done = task.state == "1_done"
            moved_into_active_sprint = (
                track_sprint_assignment
                and original_sprints[task.id] != sprint
                and sprint.state == "active"
            )
            if (
                sprint.state != "active"
                or was_done == is_done
                or moved_into_active_sprint
            ):
                continue
            sprint._append_scope_events("completed" if is_done else "reopened", task)

    def write(self, values):
        self.check_access("write")
        if values.get("sprint_id"):
            values = self._prepare_sprint_team(values, self.agile_team_id)
        track_sprint_assignment = "sprint_id" in values
        track_story_points = bool(
            {"agile_story_points", "agile_item_type_id"} & values.keys()
        )
        track_completion = "state" in values
        track_scope_context = track_sprint_assignment or track_story_points
        original_sprints = (
            {task.id: task.sprint_id for task in self} if track_scope_context else {}
        )
        original_story_points = (
            {task.id: task.agile_effective_story_points for task in self}
            if track_scope_context
            else {}
        )
        if track_sprint_assignment:
            requested_sprint = (
                self.env["project.sprint"].browse(values["sprint_id"]).exists()
            )
            if requested_sprint:
                self._validate_sprint_assignment(requested_sprint)
            if not self.env.is_superuser() and any(
                sprint.state == "closed" and sprint != requested_sprint
                for sprint in original_sprints.values()
            ):
                raise ValidationError(
                    _("Tasks cannot be removed from a closed Sprint.")
                )
        original_done_states = (
            {task.id: task.state == "1_done" for task in self}
            if track_completion
            else {}
        )
        result = super().write(values)
        if track_sprint_assignment:
            self._track_active_sprint_assignment_changes(
                original_sprints, original_story_points
            )
        if track_story_points:
            self._track_active_sprint_reestimates(
                original_sprints, original_story_points
            )
        if track_completion:
            self._track_active_sprint_completion_edges(
                original_sprints, original_done_states, track_sprint_assignment
            )
        return result

    def _write_sprint_close_assignment(self, target_sprint=False):
        """Move unfinished work without converting close into ordinary scope removal."""
        return super().write(
            {"sprint_id": target_sprint.id if target_sprint else False}
        )

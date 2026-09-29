"""Current-user snapshot and navigation boundaries for Agile planning."""

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


_BACKLOG_PAGE_SIZE = 50
_SPRINT_LIMIT = 20
_SPRINT_TASK_LIMIT = 100
_CURSOR_FIELDS = {"id", "sequence"}


class ProjectProject(models.Model):
    """Expose bounded planning data without changing Scrum's business truth."""

    _inherit = "project.project"

    @api.model
    def get_agile_planning_snapshot(self, project_id, cursor=False):
        """Return the current user's bounded read-only planning data for one project."""
        project = self._get_available_agile_planning_project(project_id)
        cursor_values = self._parse_agile_planning_cursor(cursor)
        sprints = self._get_agile_planning_sprints(project)
        sprint_tasks = self._get_agile_planning_sprint_tasks(sprints)
        current_points = self._get_current_sprint_points(sprints)
        committed_points = self._get_committed_sprint_points(sprints)
        backlog = self._get_agile_planning_backlog(project, cursor_values)

        return {
            "project": {"id": project.id, "name": project.display_name},
            "sprints": [
                {
                    "id": sprint.id,
                    "name": sprint.name,
                    "team": sprint.team_id.display_name,
                    "state": sprint.state,
                    "goal": sprint.goal or "",
                    "version": self._agile_planning_record_version(sprint),
                    "items": [self._serialize_agile_planning_task(task) for task in sprint_tasks[sprint.id]],
                    "current_points": current_points.get(sprint.id, 0.0),
                    "committed_points": committed_points.get(sprint.id, 0.0),
                }
                for sprint in sprints
            ],
            "backlog": backlog,
        }

    def action_open_agile_planning(self):
        """Open the additive client action for an available Agile project."""
        self._check_agile_planning_project()
        return {
            "type": "ir.actions.client",
            "tag": "project_agile_ui.planning",
            "context": {"project_id": self.id},
        }

    def action_open_agile_planning_sprints(self):
        """Open the standard Sprint list scoped to this planning project."""
        self._check_agile_planning_project()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Sprints"),
            "res_model": "project.sprint",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("project_scrum.view_project_sprint_list").id, "list"),
                (False, "form"),
            ],
            "search_view_id": self.env.ref("project_scrum.view_project_sprint_search").id,
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_open_agile_planning_backlog(self):
        """Open the standard Product Backlog list scoped to this planning project."""
        self._check_agile_planning_project()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Product Backlog"),
            "res_model": "project.task",
            "view_mode": "list,kanban,form",
            "views": [
                (self.env.ref("project_agile.view_task_list_agile_backlog").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            "search_view_id": self.env.ref("project_scrum.view_task_search_scrum").id,
            "domain": self._agile_planning_backlog_domain(),
            "context": {"default_project_id": self.id},
        }

    @api.model
    def _get_available_agile_planning_project(self, project_id):
        if not isinstance(project_id, int) or isinstance(project_id, bool) or project_id <= 0:
            raise ValidationError(self.env._("Choose a valid Agile project."))
        company_ids = self.env.companies.ids
        project = self.search_fetch(
            [
                ("id", "=", project_id),
                ("active", "=", True),
                ("is_template", "=", False),
                ("agile_enabled", "=", True),
                ("company_id", "in", [False, *company_ids]),
            ],
            ["display_name"],
            limit=1,
        )
        if not project:
            raise AccessError(self.env._("The Agile planning workspace is unavailable."))
        return project

    @api.model
    def _parse_agile_planning_cursor(self, cursor):
        if cursor in (False, None):
            return False
        if not isinstance(cursor, dict) or set(cursor) != _CURSOR_FIELDS:
            raise ValidationError(self.env._("The Product Backlog cursor is invalid."))
        sequence = cursor["sequence"]
        record_id = cursor["id"]
        if (
            not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or not isinstance(record_id, int)
            or isinstance(record_id, bool)
            or record_id <= 0
        ):
            raise ValidationError(self.env._("The Product Backlog cursor is invalid."))
        return {"sequence": sequence, "id": record_id}

    def _check_agile_planning_project(self):
        self.ensure_one()
        self.check_access("read")
        if not self.active or self.is_template or not self.agile_enabled:
            raise ValidationError(
                self.env._("Sprint Planning is available only for active Agile projects.")
            )
        if self.company_id and self.company_id not in self.env.companies:
            raise AccessError(self.env._("The Agile planning workspace is unavailable."))
        return self

    def _get_agile_planning_sprints(self, project):
        return self.env["project.sprint"].search_fetch(
            [
                ("project_id", "=", project.id),
                ("company_id", "in", [False, *self.env.companies.ids]),
                ("state", "in", ["draft", "active"]),
                ("team_id.active", "=", True),
            ],
            ["name", "team_id", "state", "goal"],
            limit=_SPRINT_LIMIT,
            order="state, date_start desc, id desc",
        )

    def _get_agile_planning_sprint_tasks(self, sprints):
        tasks = self.env["project.task"].search_fetch(
            [
                ("sprint_id", "in", sprints.ids),
                ("company_id", "in", [False, *self.env.companies.ids]),
                ("active", "=", True),
            ],
            ["name", "agile_key", "agile_item_type_id", "agile_story_points", "agile_backlog_sequence"],
            limit=_SPRINT_TASK_LIMIT,
            order="agile_backlog_sequence, id",
        )
        result = {sprint.id: self.env["project.task"] for sprint in sprints}
        for task in tasks:
            result[task.sprint_id.id] |= task
        return result

    def _get_current_sprint_points(self, sprints):
        rows = self.env["project.task"]._read_group(
            [("sprint_id", "in", sprints.ids)],
            ["sprint_id"],
            ["agile_story_points:sum"],
        )
        return {sprint.id: points or 0.0 for sprint, points in rows}

    def _get_committed_sprint_points(self, sprints):
        rows = self.env["project.sprint.scope.event"]._read_group(
            [("sprint_id", "in", sprints.ids), ("event_type", "=", "committed")],
            ["sprint_id"],
            ["story_points:sum"],
        )
        return {sprint.id: points or 0.0 for sprint, points in rows}

    def _agile_planning_backlog_domain(self, cursor=False):
        self.ensure_one()
        domain = [
            ("project_id", "=", self.id),
            ("company_id", "in", [False, *self.env.companies.ids]),
            ("active", "=", True),
            ("agile_item_type_id.can_schedule_in_sprint", "=", True),
            ("sprint_id", "=", False),
            ("has_template_ancestor", "=", False),
            ("has_project_template", "=", False),
        ]
        if cursor:
            domain.extend(
                [
                    "|",
                    ("agile_backlog_sequence", ">", cursor["sequence"]),
                    "&",
                    ("agile_backlog_sequence", "=", cursor["sequence"]),
                    ("id", ">", cursor["id"]),
                ]
            )
        return domain

    def _get_agile_planning_backlog(self, project, cursor):
        tasks = self.env["project.task"].search_fetch(
            project._agile_planning_backlog_domain(cursor),
            [
                "name",
                "agile_key",
                "agile_item_type_id",
                "agile_story_points",
                "agile_backlog_sequence",
                "parent_id",
            ],
            limit=_BACKLOG_PAGE_SIZE + 1,
            order="agile_backlog_sequence, id",
        )
        visible_tasks = tasks[:_BACKLOG_PAGE_SIZE]
        has_next_page = len(tasks) > len(visible_tasks)
        return {
            "items": [self._serialize_agile_planning_task(task) for task in visible_tasks],
            "next_cursor": (
                {
                    "sequence": visible_tasks[-1].agile_backlog_sequence,
                    "id": visible_tasks[-1].id,
                }
                if has_next_page
                else False
            ),
        }

    def _serialize_agile_planning_task(self, task):
        return {
            "id": task.id,
            "name": task.name,
            "agile_key": task.agile_key,
            "item_type": task.agile_item_type_id.display_name,
            "story_points": task.agile_story_points,
            "parent": task.parent_id.display_name or None,
            "version": self._agile_planning_record_version(task),
        }

    @api.model
    def apply_agile_planning_change(
        self, project_id, operation, task_ids, *, sprint_id=False, before_task_id=False, expected_versions=False
    ):
        """Apply one current-user planning intent then return a reconciled snapshot.

        The client supplies only record identities and read versions. The server resolves
        current access, eligibility, lifecycle, and ordering state under row locks.
        """
        project = self._get_available_agile_planning_project(project_id)
        if operation not in {"assign", "return", "reorder"}:
            raise ValidationError(self.env._("Choose a valid Sprint Planning operation."))
        tasks = self._get_agile_planning_change_tasks(project, task_ids)
        expected_versions = self._parse_agile_planning_versions(expected_versions)
        with self.env.cr.savepoint():
            if operation == "assign":
                self._apply_agile_planning_assignment(project, tasks, sprint_id, expected_versions)
            elif operation == "return":
                self._apply_agile_planning_return(project, tasks, expected_versions)
            else:
                self._apply_agile_planning_reorder(project, tasks, before_task_id, expected_versions)
        return self.get_agile_planning_snapshot(project.id)

    @api.model
    def _get_agile_planning_change_tasks(self, project, task_ids):
        if not isinstance(task_ids, list) or not task_ids:
            raise ValidationError(self.env._("Select one or more Product Backlog items."))
        if any(not isinstance(task_id, int) or isinstance(task_id, bool) or task_id <= 0 for task_id in task_ids):
            raise ValidationError(self.env._("The selected Product Backlog items are invalid."))
        if len(set(task_ids)) != len(task_ids):
            raise ValidationError(self.env._("Select each Product Backlog item only once."))
        tasks = self.env["project.task"].search([("id", "in", task_ids), ("project_id", "=", project.id)])
        if len(tasks) != len(task_ids):
            raise AccessError(self.env._("One or more selected Product Backlog items are unavailable."))
        tasks.check_access("write")
        return tasks

    @api.model
    def _parse_agile_planning_versions(self, expected_versions):
        if not isinstance(expected_versions, dict):
            raise ValidationError(self.env._("Refresh Sprint Planning before changing it."))
        return expected_versions

    @api.model
    def _agile_planning_record_version(self, record):
        write_date = fields.Datetime.to_string(record.write_date)
        if record._name == "project.task":
            return f"{record.id}:{write_date}:{record.sprint_id.id or 0}:{record.agile_backlog_sequence}:{record.name}"
        return f"{record.id}:{write_date}:{record.state}:{record.team_id.active}"

    @api.model
    def _check_agile_planning_versions(self, records, expected_versions):
        for record in records:
            expected = expected_versions.get(str(record.id), expected_versions.get(record.id))
            if not isinstance(expected, str) or expected != self._agile_planning_record_version(record):
                raise ValidationError(self.env._("Sprint Planning changed. Refresh and retry your action."))

    @api.model
    def _lock_agile_planning_records(self, table, record_ids):
        if not record_ids:
            return
        self.env.cr.execute(f"SELECT id FROM {table} WHERE id IN %s ORDER BY id FOR UPDATE", [tuple(sorted(record_ids))])
        if len(self.env.cr.fetchall()) != len(record_ids):
            raise ValidationError(self.env._("A selected planning record no longer exists."))

    @api.model
    def _require_agile_planning_backlog_tasks(self, project, tasks):
        available = self.env["project.task"].search(project._agile_planning_backlog_domain() + [("id", "in", tasks.ids)])
        if len(available) != len(tasks):
            raise ValidationError(self.env._("Only current Product Backlog items can be changed here."))

    @api.model
    def _apply_agile_planning_assignment(self, project, tasks, sprint_id, expected_versions):
        if not isinstance(sprint_id, int) or isinstance(sprint_id, bool) or sprint_id <= 0:
            raise ValidationError(self.env._("Choose a valid draft Sprint."))
        sprint = self.env["project.sprint"].search([("id", "=", sprint_id), ("project_id", "=", project.id)], limit=1)
        if not sprint:
            raise AccessError(self.env._("The target Sprint is unavailable."))
        sprint.check_access("read")
        self._lock_agile_planning_records("project_sprint", sprint.ids)
        self._lock_agile_planning_records("project_task", tasks.ids)
        sprint.invalidate_recordset(["state", "project_id", "company_id", "team_id", "write_date"])
        tasks.invalidate_recordset(["sprint_id", "project_id", "company_id", "agile_item_type_id", "write_date"])
        self._check_agile_planning_versions(tasks, expected_versions)
        self._check_agile_planning_versions(sprint, expected_versions)
        self._require_agile_planning_backlog_tasks(project, tasks)
        if not sprint.team_id.active:
            raise ValidationError(self.env._("The target Sprint needs an active Agile team."))
        tasks.assign_product_backlog_to_sprint(sprint, draft_only=True)

    @api.model
    def _apply_agile_planning_return(self, project, tasks, expected_versions):
        self._lock_agile_planning_records("project_task", tasks.ids)
        tasks.invalidate_recordset(["sprint_id", "project_id", "company_id", "write_date"])
        sprints = tasks.mapped("sprint_id")
        if not sprints or any(sprint.project_id != project or sprint.company_id != project.company_id for sprint in sprints):
            raise ValidationError(self.env._("Only this project's Sprint Backlog items can be returned."))
        self._lock_agile_planning_records("project_sprint", sprints.ids)
        sprints.invalidate_recordset(["state", "project_id", "company_id", "write_date"])
        self._check_agile_planning_versions(tasks, expected_versions)
        self._check_agile_planning_versions(sprints, expected_versions)
        if any(sprint.state == "closed" for sprint in sprints):
            raise ValidationError(self.env._("Tasks cannot be removed from a closed Sprint."))
        tasks.return_sprint_tasks_to_product_backlog()

    @api.model
    def _apply_agile_planning_reorder(self, project, tasks, before_task_id, expected_versions):
        if len(tasks) != 1:
            raise ValidationError(self.env._("Reorder one Product Backlog item at a time."))
        if before_task_id is not False and (not isinstance(before_task_id, int) or isinstance(before_task_id, bool) or before_task_id <= 0):
            raise ValidationError(self.env._("The Product Backlog ordering target is invalid."))
        domain = project._agile_planning_backlog_domain()
        backlog = self.env["project.task"].search(domain, order="agile_backlog_sequence, id")
        self._lock_agile_planning_records("project_task", backlog.ids)
        backlog.invalidate_recordset(["agile_backlog_sequence", "sprint_id", "write_date"])
        self._require_agile_planning_backlog_tasks(project, tasks)
        before_task = backlog.filtered(lambda task: task.id == before_task_id)
        if before_task_id and not before_task:
            raise AccessError(self.env._("The Product Backlog ordering target is unavailable."))
        self._check_agile_planning_versions(tasks | before_task, expected_versions)
        ordered_tasks = backlog - tasks
        if before_task:
            insertion_index = ordered_tasks.ids.index(before_task.id)
            ordered_tasks = ordered_tasks[:insertion_index] | tasks | ordered_tasks[insertion_index:]
        else:
            ordered_tasks |= tasks
        for index, task in enumerate(ordered_tasks, start=1):
            task.write({"agile_backlog_sequence": index * 10})

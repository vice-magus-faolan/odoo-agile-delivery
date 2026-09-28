"""Current-user snapshot and navigation boundaries for Agile planning."""

from odoo import api, models
from odoo.exceptions import AccessError, ValidationError


_BACKLOG_PAGE_SIZE = 50
_SPRINT_LIMIT = 20
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
            "items": [
                {
                    "id": task.id,
                    "name": task.name,
                    "agile_key": task.agile_key,
                    "item_type": task.agile_item_type_id.display_name,
                    "story_points": task.agile_story_points,
                    "parent": task.parent_id.display_name or None,
                }
                for task in visible_tasks
            ],
            "next_cursor": (
                {
                    "sequence": visible_tasks[-1].agile_backlog_sequence,
                    "id": visible_tasks[-1].id,
                }
                if has_next_page
                else False
            ),
        }

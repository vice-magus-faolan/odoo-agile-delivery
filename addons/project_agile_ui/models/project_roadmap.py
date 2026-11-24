"""Caller-owned roadmap of native dates, never another scheduling engine."""

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

_PAGE_SIZE = 50


class ProjectProject(models.Model):
    """Compose work deadlines and release milestones without changing either."""

    # Separate read-only projection from the planning mutation boundary.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "project.project"

    def action_open_agile_roadmap(self):
        """Open the optional roadmap for this available Agile Project."""
        self._check_agile_planning_project()
        return {
            "type": "ir.actions.client",
            "tag": "project_agile_ui.roadmap",
            "context": {"project_id": self.id},
        }

    @api.model
    def _agile_roadmap_window(self, date_from, date_to):
        try:
            start = fields.Date.to_date(date_from)
            end = fields.Date.to_date(date_to)
        except (ValueError, TypeError, AssertionError) as error:
            raise ValidationError(self.env._("Choose valid roadmap dates.")) from error
        if not start or not end or not 0 <= (end - start).days < 366:
            raise ValidationError(
                self.env._("Choose a roadmap window of 1 to 366 days.")
            )
        return start, end

    @api.model
    def _agile_roadmap_scope(self, project_id, team_id, milestone_id, item_type_id):
        project = self._get_available_agile_planning_project(project_id)
        team = self._get_agile_planning_team(project, team_id)
        milestone = self._get_agile_planning_milestone(project, milestone_id)
        domain = Domain(
            [
                ("project_id", "=", project.id),
                ("company_id", "in", [False, *self.env.companies.ids]),
                ("active", "=", True),
                ("has_template_ancestor", "=", False),
                ("has_project_template", "=", False),
                ("state", "not in", ["1_done", "1_canceled"]),
            ]
        )
        if team:
            domain &= Domain("agile_team_id", "=", team.id)
        if milestone:
            domain &= Domain("milestone_id", "=", milestone.id)
        if item_type_id is not False and item_type_id is not None:
            if type(item_type_id) is not int or item_type_id <= 0:
                raise ValidationError(self.env._("Choose a valid item type."))
            if not self.env["project.agile.item.type"].search(
                [("id", "=", item_type_id)], limit=1
            ):
                raise AccessError(self.env._("The item type is unavailable."))
            domain &= Domain("agile_item_type_id", "=", item_type_id)
        return project, domain

    @api.model
    def _agile_roadmap_start_field(self):
        # Enterprise may provide native planned starts. Community assignment dates
        # are telemetry, not a substitute. fields_get also honors field groups.
        definition = self.env["project.task"].fields_get(["planned_date_begin"])
        if definition.get("planned_date_begin", {}).get("type") in ("date", "datetime"):
            return "planned_date_begin"
        return False

    @api.model
    def _agile_roadmap_date_domain(self, start, end, mode, start_field=False):
        if mode == "unscheduled":
            return Domain("date_deadline", "=", False)
        if mode != "window":
            raise ValidationError(self.env._("Choose dated or unscheduled work."))
        after = fields.Datetime.to_string(end + timedelta(days=1))
        domain = Domain("date_deadline", ">=", str(start))
        if start_field:
            domain &= Domain.OR(
                [
                    Domain(start_field, "<", after),
                    Domain(start_field, "=", False)
                    & Domain("date_deadline", "<", after),
                ]
            )
        else:
            domain &= Domain("date_deadline", "<", after)
        return domain

    def _agile_roadmap_labels(self, tasks, show_milestones):
        """Resolve related identities independently under current caller rules."""
        related = {
            "type": ("project.agile.item.type", tasks.agile_item_type_id.ids),
            "team": ("project.agile.team", tasks.agile_team_id.ids),
            "parent": ("project.task", tasks.parent_id.ids),
        }
        if show_milestones:
            related["milestone"] = ("project.milestone", tasks.milestone_id.ids)
        result = {}
        for key, (model, ids) in related.items():
            domain = Domain("id", "in", ids)
            if key != "type":
                domain &= Domain("project_id", "=", self.id)
            rows = (
                self.env[model]
                .with_context(active_test=False)
                .search_fetch(domain, ["name"], limit=_PAGE_SIZE)
            )
            result[key] = {row.id: {"id": row.id, "name": row.name} for row in rows}
        return result

    def _agile_roadmap_items(self, tasks, start_field, show_milestones):
        labels = self._agile_roadmap_labels(tasks, show_milestones)
        return [
            {
                "id": task.id,
                "key": task.agile_key,
                "name": task.name,
                "start": fields.Datetime.to_string(task[start_field])
                if start_field
                else False,
                "end": fields.Datetime.to_string(task.date_deadline),
                "type": labels["type"].get(task.agile_item_type_id.id, False),
                "team": labels["team"].get(task.agile_team_id.id, False),
                "parent": labels["parent"].get(task.parent_id.id, False),
                "parent_unavailable": bool(task.parent_id)
                and task.parent_id.id not in labels["parent"],
                "milestone": labels.get("milestone", {}).get(
                    task.milestone_id.id, False
                )
                if show_milestones
                else False,
            }
            for task in tasks
        ]

    @api.model
    def get_agile_roadmap_snapshot(
        self,
        project_id,
        date_from,
        date_to,
        mode="window",
        team_id=False,
        milestone_id=False,
        item_type_id=False,
        task_cursor=False,
        milestone_cursor=False,
    ):
        """Return independent live pages with complete caller-visible counts."""
        start, end = self._agile_roadmap_window(date_from, date_to)
        project, base_domain = self._agile_roadmap_scope(
            project_id, team_id, milestone_id, item_type_id
        )
        start_field = self._agile_roadmap_start_field()
        domain = base_domain & self._agile_roadmap_date_domain(
            start, end, mode, start_field
        )
        scope = {
            "project": project.id,
            "team": team_id or False,
            "milestone": milestone_id or False,
            "type": item_type_id or False,
            "from": str(start),
            "to": str(end),
            "mode": mode,
            "companies": self.env.companies.ids,
        }
        task_fields = [
            "name",
            "agile_key",
            "agile_item_type_id",
            "agile_team_id",
            "parent_id",
            "milestone_id",
            "date_deadline",
            "write_date",
        ]
        if start_field:
            task_fields.append(start_field)
        tasks, next_task = self._agile_planning_page(
            "project.task",
            domain,
            task_fields,
            [("id", "asc")],
            _PAGE_SIZE,
            task_cursor,
            {**scope, "page": "roadmap_work"},
        )
        show_milestones = project.allow_milestones and self.env.user.has_group(
            "project.group_project_milestone"
        )
        milestones = (
            project._agile_roadmap_milestones(
                start, end, mode, milestone_id, milestone_cursor, scope
            )
            if show_milestones
            else {"items": [], "total": 0, "next_cursor": False}
        )
        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "start": fields.Date.to_string(project.date_start),
                "end": fields.Date.to_string(project.date),
            },
            "native_task_start": bool(start_field),
            "show_milestones": bool(show_milestones),
            "work": {
                "items": project._agile_roadmap_items(
                    tasks, start_field, show_milestones
                ),
                "total": self.env["project.task"].search_count(domain),
                "next_cursor": next_task,
            },
            "milestones": milestones,
        }

    def _agile_roadmap_milestones(self, start, end, mode, milestone_id, cursor, scope):
        domain = Domain("project_id", "=", self.id)
        if milestone_id:
            domain &= Domain("id", "=", milestone_id)
        if mode == "unscheduled":
            domain &= Domain("deadline", "=", False)
        else:
            domain &= Domain("deadline", ">=", str(start)) & Domain(
                "deadline", "<=", str(end)
            )
        rows, continuation = self._agile_planning_page(
            "project.milestone",
            domain,
            ["name", "deadline", "is_reached", "write_date"],
            [("id", "asc")],
            _PAGE_SIZE,
            cursor,
            {**scope, "page": "roadmap_releases"},
        )
        return {
            "items": [
                {
                    "id": row.id,
                    "name": row.name,
                    "date": fields.Date.to_string(row.deadline),
                    "reached": row.is_reached,
                }
                for row in rows
            ],
            "total": self.env["project.milestone"].search_count(domain),
            "next_cursor": continuation,
        }

    def action_open_agile_roadmap_work(
        self,
        team_id=False,
        milestone_id=False,
        item_type_id=False,
    ):
        """Open all filtered open work, including other windows and missing dates."""
        self.ensure_one()
        project, domain = self._agile_roadmap_scope(
            self.id, team_id, milestone_id, item_type_id
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Roadmap work — all dates"),
            "res_model": "project.task",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("project_agile_ui.view_task_list_roadmap").id, "list"),
                (False, "form"),
            ],
            "search_view_id": self.env.ref("project_scrum.view_task_search_scrum").id,
            "domain": list(domain),
            "context": {
                "default_project_id": project.id,
                "allow_milestones": project.allow_milestones,
            },
        }

    def action_open_agile_roadmap_milestone(self, milestone_id):
        """Recheck Project and milestone visibility before native navigation."""
        self._check_agile_planning_project()
        milestone = self._get_agile_planning_milestone(self, milestone_id)
        if not milestone:
            raise AccessError(self.env._("The planning milestone is unavailable."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.milestone",
            "res_id": milestone.id,
            "views": [(False, "form")],
            "target": "current",
        }

"""Bounded, caller-owned Active Sprint presentation; native Tasks own edits."""

from odoo import api, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

_CARD_LIMIT = 50
_ANCESTOR_LIMIT = 32
_CARD_FIELDS = [
    "name",
    "agile_key",
    "agile_item_type_id",
    "parent_id",
    "stage_id",
    "write_date",
]


class ProjectProject(models.Model):
    """Keep read-only Sprint visualization separate from planning mutations."""

    # The matrix has no planning writes; share only resolution and paging.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "project.project"

    def action_open_agile_swimlanes(self):
        """Open an optional presentation, leaving native Active Sprint intact."""
        self._check_agile_planning_project()
        return {
            "type": "ir.actions.client",
            "tag": "project_agile_ui.swimlanes",
            "context": {"project_id": self.id},
        }

    @api.model
    def _agile_swimlane_scope(self, project_id, team_id, sprint_id):
        project = self._get_available_agile_planning_project(project_id)
        team = self._get_agile_planning_team(project, team_id)
        if team and not team.active:
            raise AccessError(self.env._("The Agile planning team is unavailable."))
        sprint_domain = Domain(
            [
                ("project_id", "=", project.id),
                ("company_id", "in", [False, *self.env.companies.ids]),
                ("state", "=", "active"),
                ("team_id.active", "=", True),
            ]
        )
        if team:
            sprint_domain &= Domain("team_id", "=", team.id)
        if sprint_id is not False and sprint_id is not None:
            if type(sprint_id) is not int or sprint_id <= 0:
                raise ValidationError(self.env._("Choose a valid Active Sprint."))
            sprint_domain &= Domain("id", "=", sprint_id)
            if not self.env["project.sprint"].search(sprint_domain, limit=1):
                raise AccessError(self.env._("The Active Sprint is unavailable."))
        # A caller-bound subquery preserves Sprint record rules without loading
        # every Active Sprint identity into Python or trusting relational prefetch.
        sprints = self.env["project.sprint"]._search(sprint_domain)
        domain = Domain(
            [
                ("project_id", "=", project.id),
                ("company_id", "in", [False, *self.env.companies.ids]),
                ("active", "=", True),
                ("is_template", "=", False),
                ("sprint_id", "in", sprints),
            ]
        )
        return project, domain, sprint_domain

    @api.model
    def get_agile_swimlane_snapshot(
        self, project_id, grouping="epic", team_id=False, sprint_id=False, cursor=False
    ):
        """Partition one card window; the unique total covers the complete filter."""
        if not isinstance(grouping, str) or grouping not in ("epic", "assignee"):
            raise ValidationError(self.env._("Choose Epic or assignee lanes."))
        project, domain, _sprint_domain = self._agile_swimlane_scope(
            project_id, team_id, sprint_id
        )
        tasks, continuation = self._agile_planning_page(
            "project.task",
            domain,
            _CARD_FIELDS,
            [("id", "asc")],
            _CARD_LIMIT,
            cursor,
            {
                "page": "swimlanes",
                "project": project.id,
                "team": team_id or False,
                "sprint": sprint_id or False,
                "grouping": grouping,
                "revision": project.agile_planning_backlog_revision,
            },
        )
        stages = self.env["project.task.type"].search_fetch(
            [("id", "in", tasks.stage_id.ids)], ["name"], order="sequence, id"
        )
        stage_names = {row.id: row.name for row in stages}
        lanes = self._agile_swimlane_lanes(project, tasks, grouping)
        return {
            "project": {"id": project.id, "name": project.display_name},
            "total": self.env["project.task"].search_count(domain),
            "shown": len(tasks),
            "next_cursor": continuation,
            "stages": [{"id": row.id, "name": row.name} for row in stages]
            + (
                [{"id": 0, "name": self.env._("No visible stage")}]
                if any(task.stage_id.id not in stage_names for task in tasks)
                else []
            ),
            "lanes": self._agile_swimlane_cards(tasks, lanes, stage_names),
        }

    def _agile_swimlane_ancestors(self, project, tasks):
        """Read bounded ancestry in batches, never through an unreadable parent."""
        known = {row.id: row for row in tasks}
        pending = set(tasks.parent_id.ids) - known.keys()
        for _depth in range(_ANCESTOR_LIMIT):
            if not pending:
                break
            parents = (
                self.env["project.task"]
                .with_context(active_test=False)
                .search_fetch(
                    [
                        ("id", "in", list(pending)),
                        ("project_id", "=", project.id),
                        ("company_id", "in", [False, *self.env.companies.ids]),
                        ("is_template", "=", False),
                    ],
                    ["name", "agile_key", "parent_id", "agile_item_type_id"],
                    limit=_CARD_LIMIT,
                )
            )
            known.update({row.id: row for row in parents})
            pending = set(parents.parent_id.ids) - known.keys()
        return known

    def _agile_swimlane_epic(self, task, known, epic_id):
        current = task
        # Inspect the card itself, then at most 32 fetched ancestors.
        for _depth in range(_ANCESTOR_LIMIT + 1):
            if epic_id and current.agile_item_type_id.id == epic_id:
                return f"epic:{current.id}", f"{current.agile_key} · {current.name}"
            if not current.parent_id:
                return "none", self.env._("No Epic")
            current = known.get(current.parent_id.id)
            if current is None:
                break
        return "unknown", self.env._("Epic context unavailable")

    def _agile_swimlane_lanes(self, project, tasks, grouping):
        if grouping == "epic":
            epic = self.env.ref(
                "project_agile.project_agile_item_type_epic", raise_if_not_found=False
            )
            known = self._agile_swimlane_ancestors(project, tasks)
            return {
                row.id: self._agile_swimlane_epic(
                    row, known, epic.id if epic else False
                )
                for row in tasks
            }
        # Only these caller-authorized cards may supply assignment cardinality.
        # Native Many2many reads filter hidden users, and their cache is shared
        # across sudo environments. Discard both a warmed filtered value and the
        # privileged result; never elevate Task discovery or user-name reads.
        tasks.invalidate_recordset(["user_ids"])
        try:
            assignments = {
                row["id"]: row["user_ids"]
                for row in tasks.sudo().read(["user_ids"], load=None)
            }
        finally:
            tasks.invalidate_recordset(["user_ids"])
        single_ids = {ids[0] for ids in assignments.values() if len(ids) == 1}
        users = (
            self.env["res.users"]
            .with_context(active_test=False)
            .search_fetch([("id", "in", list(single_ids))], ["name"], limit=_CARD_LIMIT)
        )
        names = {row.id: row.name for row in users}
        return {
            task_id: self._agile_swimlane_assignee(user_ids, names)
            for task_id, user_ids in assignments.items()
        }

    def _agile_swimlane_assignee(self, user_ids, names):
        if not user_ids:
            return "none", self.env._("Unassigned")
        if len(user_ids) > 1:
            return "multiple", self.env._("Multiple assignees")
        user_id = user_ids[0]
        if user_id not in names:
            return "unknown", self.env._("Assignee unavailable")
        return f"user:{user_id}", names[user_id]

    def _agile_swimlane_cards(self, tasks, lane_keys, stage_names):
        lanes = {}
        for task in tasks:
            key, name = lane_keys[task.id]
            lane = lanes.setdefault(key, {"id": key, "name": name, "items": []})
            lane["items"].append(
                {
                    "id": task.id,
                    "name": task.name,
                    "key": task.agile_key,
                    "stage_id": task.stage_id.id
                    if task.stage_id.id in stage_names
                    else 0,
                }
            )
        return list(lanes.values())

    def action_open_agile_swimlane_tasks(
        self, team_id=False, sprint_id=False, task_ids=None
    ):
        """Open the complete filtered list or exactly the labeled lane window."""
        self.ensure_one()
        project, domain, sprint_domain = self._agile_swimlane_scope(
            self.id, team_id, sprint_id
        )
        # Window actions cross JSON: never serialize an ORM Query or enumerate
        # unbounded Sprint IDs. A selected Sprint always fits this fallback.
        sprints = self.env["project.sprint"].search(sprint_domain, limit=101)
        if len(sprints) > 100:
            raise ValidationError(
                self.env._(
                    "Choose one Active Sprint before opening the native work list "
                    "when more than 100 Active Sprints match."
                )
            )
        domain = domain.map_conditions(
            lambda condition: Domain("sprint_id", "in", sprints.ids)
            if condition.field_expr == "sprint_id"
            else condition
        )
        if task_ids is not None:
            if (
                not isinstance(task_ids, list)
                or len(task_ids) > _CARD_LIMIT
                or any(type(value) is not int or value <= 0 for value in task_ids)
            ):
                raise ValidationError(self.env._("The lane window is invalid."))
            domain &= Domain("id", "in", task_ids)
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Active Sprint work"),
            "res_model": "project.task",
            "view_mode": "list,kanban,form",
            "views": [(False, "list"), (False, "kanban"), (False, "form")],
            "domain": list(domain),
            "context": {"default_project_id": project.id},
        }

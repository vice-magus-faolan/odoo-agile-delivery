"""Current-user snapshot and navigation boundaries for Agile planning."""

from psycopg2.errors import SerializationFailure

from odoo import api, fields, models
from odoo.exceptions import AccessError, ConcurrencyError, ValidationError
from odoo.fields import Domain

_BACKLOG_PAGE_SIZE = 50
_MAX_MUTATION_TASKS = 20
_SPRINT_LIMIT = 20
_SPRINT_TASK_LIMIT = 100
_CURSOR_FIELDS = {"id", "revision", "sequence"}
_VERSION_NAMESPACES = {"sprints", "tasks"}


class ProjectProject(models.Model):
    """Expose bounded planning data without changing Scrum's business truth."""

    _inherit = "project.project"

    agile_planning_backlog_revision = fields.Integer(
        default=0, copy=False, readonly=True
    )

    @api.model
    def get_agile_planning_snapshot(
        self,
        project_id,
        cursor=False,
        team_id=False,
        milestone_id=False,
        *,
        sprint_cursor=False,
        task_cursor=False,
        team_cursor=False,
    ):
        """Return the current user's bounded read-only planning data for one project."""
        project = self._get_available_agile_planning_project(project_id)
        team = self._get_agile_planning_team(project, team_id)
        milestone = self._get_agile_planning_milestone(project, milestone_id)
        show_milestones = project.allow_milestones and self.env.user.has_group(
            "project.group_project_milestone"
        )
        cursor_values = self._parse_agile_planning_cursor(cursor)
        if cursor_values and (
            cursor_values["revision"] != project.agile_planning_backlog_revision
            or cursor_values.get("team_id", False) != (team.id or False)
            or cursor_values.get("milestone_id", False) != (milestone.id or False)
        ):
            raise ValidationError(
                self.env._("The Product Backlog changed. Refresh and retry.")
            )
        scope = {
            "project": project.id,
            "team": team.id or False,
            "milestone": milestone.id or False,
            "revision": project.agile_planning_backlog_revision,
        }
        sprints, next_sprint = self._get_agile_planning_sprints(
            project, team, sprint_cursor, scope
        )
        task_domain = self._agile_planning_sprint_task_domain(sprints, milestone)
        sprint_tasks, next_task = self._get_agile_planning_sprint_tasks(
            sprints, task_domain, task_cursor, scope
        )
        current_points, item_counts = self._get_current_sprint_points(task_domain)
        committed_points = self._get_committed_sprint_points(sprints, task_domain)
        backlog_tasks, next_cursor = self._get_agile_planning_backlog(
            project, cursor_values, team, milestone
        )
        visible_tasks = backlog_tasks
        for tasks in sprint_tasks.values():
            visible_tasks |= tasks
        # Resolve names through caller-bound search, not privileged related prefetch.
        milestones = self.env["project.milestone"]
        if show_milestones:
            milestones = milestones.search_fetch(
                [
                    ("id", "in", visible_tasks.milestone_id.ids),
                    ("project_id", "=", project.id),
                ],
                ["name"],
            )
        milestone_names = {row.id: row.name for row in milestones}
        teams, next_team = self._agile_planning_page(
            "project.agile.team",
            [("project_id", "=", project.id)],
            ["name", "active", "write_date"],
            [("id", "asc")],
            100,
            team_cursor,
            {**scope, "page": "teams"},
        )
        teams |= team

        return {
            "project": {
                "id": project.id,
                "name": project.display_name,
                "allow_milestones": bool(show_milestones),
            },
            "milestone": {"id": milestone.id, "name": milestone.name}
            if milestone
            else False,
            "teams": [{"id": row.id, "name": row.name} for row in teams],
            "pages": {
                "sprints": next_sprint,
                "tasks": next_task,
                "teams": next_team,
            },
            "sprints": [
                {
                    "id": sprint.id,
                    "name": sprint.name,
                    "team": sprint.team_id.display_name,
                    "state": sprint.state,
                    "goal": sprint.goal or "",
                    "version": self._agile_planning_record_version(sprint),
                    "items": [
                        self._serialize_agile_planning_task(task, milestone_names)
                        for task in sprint_tasks[sprint.id]
                    ],
                    "item_count": item_counts.get(sprint.id, 0),
                    "current_points": current_points.get(sprint.id, 0.0),
                    "committed_points": committed_points.get(sprint.id, 0.0),
                }
                for sprint in sprints
            ],
            "backlog": {
                "items": [
                    self._serialize_agile_planning_task(task, milestone_names)
                    for task in backlog_tasks
                ],
                "next_cursor": next_cursor,
            },
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
            "search_view_id": self.env.ref(
                "project_scrum.view_project_sprint_search"
            ).id,
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }

    def action_open_agile_planning_backlog(self, team_id=False, milestone_id=False):
        """Open the standard Product Backlog list scoped to this planning project."""
        self._check_agile_planning_project()
        team = self._get_agile_planning_team(self, team_id)
        milestone = self._get_agile_planning_milestone(self, milestone_id)
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
            "domain": self._agile_planning_backlog_domain(
                team=team, milestone=milestone
            ),
            "context": {
                "default_project_id": self.id,
                "allow_milestones": self.allow_milestones,
            },
        }

    @api.model
    def _get_agile_planning_milestone(self, project, milestone_id):
        if milestone_id is False or milestone_id is None:
            return self.env["project.milestone"]
        if (
            not isinstance(milestone_id, int)
            or isinstance(milestone_id, bool)
            or milestone_id <= 0
        ):
            raise ValidationError(self.env._("Choose a valid milestone."))
        if not project.allow_milestones or not self.env.user.has_group(
            "project.group_project_milestone"
        ):
            raise AccessError(self.env._("The planning milestone is unavailable."))
        milestone = self.env["project.milestone"].search_fetch(
            [("id", "=", milestone_id), ("project_id", "=", project.id)],
            ["name"],
            limit=1,
        )
        if not milestone:
            raise AccessError(self.env._("The planning milestone is unavailable."))
        return milestone

    @api.model
    def _get_agile_planning_team(self, project, team_id):
        if team_id is False or team_id is None:
            return self.env["project.agile.team"]
        if not isinstance(team_id, int) or isinstance(team_id, bool) or team_id <= 0:
            raise ValidationError(self.env._("Choose a valid Agile team."))
        team = self.env["project.agile.team"].search(
            [
                ("id", "=", team_id),
                ("project_id", "=", project.id),
                ("company_id", "in", [False, *self.env.companies.ids]),
            ],
            limit=1,
        )
        if not team:
            raise AccessError(self.env._("The Agile planning team is unavailable."))
        return team

    @api.model
    def _get_available_agile_planning_project(self, project_id):
        if (
            not isinstance(project_id, int)
            or isinstance(project_id, bool)
            or project_id <= 0
        ):
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
            ["display_name", "agile_planning_backlog_revision", "allow_milestones"],
            limit=1,
        )
        if not project:
            raise AccessError(
                self.env._("The Agile planning workspace is unavailable.")
            )
        return project

    @api.model
    def _parse_agile_planning_cursor(self, cursor):
        if cursor in (False, None):
            return False
        if not isinstance(cursor, dict) or not (
            _CURSOR_FIELDS
            <= set(cursor)
            <= _CURSOR_FIELDS | {"team_id", "milestone_id"}
        ):
            raise ValidationError(self.env._("The Product Backlog cursor is invalid."))
        sequence = cursor["sequence"]
        record_id = cursor["id"]
        revision = cursor["revision"]
        if (
            not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or not isinstance(record_id, int)
            or isinstance(record_id, bool)
            or record_id <= 0
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 0
        ):
            raise ValidationError(self.env._("The Product Backlog cursor is invalid."))
        for field in ("team_id", "milestone_id"):
            value = cursor.get(field, False)
            if value is not False and (
                not isinstance(value, int) or isinstance(value, bool) or value <= 0
            ):
                raise ValidationError(
                    self.env._("The Product Backlog cursor is invalid.")
                )
        return dict(cursor)

    def _check_agile_planning_project(self):
        self.ensure_one()
        self.check_access("read")
        if not self.active or self.is_template or not self.agile_enabled:
            raise ValidationError(
                self.env._(
                    "Sprint Planning is available only for active Agile projects."
                )
            )
        if self.company_id and self.company_id not in self.env.companies:
            raise AccessError(
                self.env._("The Agile planning workspace is unavailable.")
            )
        return self

    def _agile_planning_page(
        self, model, domain, field_names, ordering, limit, cursor, scope
    ):
        """Page a caller-bound relation; a cursor is position, never authority.

        Validate its anchor in the current domain before deriving the keyset.
        Only non-null integer/selection keys are used by these three callers.
        """
        records = self.env[model]
        domain = Domain(domain)
        if cursor is not False and cursor is not None:
            if (
                not isinstance(cursor, dict)
                or set(cursor) != {"id", "version", "scope"}
                or type(cursor["id"]) is not int
                or cursor["id"] <= 0
                or not isinstance(cursor["version"], str)
                or cursor["scope"] != scope
            ):
                raise ValidationError(
                    self.env._("The planning page is invalid. Refresh and retry.")
                )
            anchor = records.search_fetch(
                domain & Domain("id", "=", cursor["id"]),
                list(dict.fromkeys([*field_names, *(key for key, _ in ordering)])),
                limit=1,
            )
            if not anchor or str(anchor.write_date) != cursor["version"]:
                raise ValidationError(
                    self.env._("The planning page changed. Refresh and retry.")
                )
            after, prefix = Domain.FALSE, Domain.TRUE
            for key, direction in ordering:
                after |= prefix & Domain(
                    key, ">" if direction == "asc" else "<", anchor[key]
                )
                prefix &= Domain(key, "=", anchor[key])
            domain &= after
        page = records.search_fetch(
            domain,
            field_names,
            limit=limit + 1,
            order=", ".join(f"{key} {direction}" for key, direction in ordering),
        )
        visible = page[:limit]
        continuation = (
            {
                "id": visible[-1].id,
                "version": str(visible[-1].write_date),
                "scope": scope,
            }
            if len(page) > limit
            else False
        )
        return visible, continuation

    def _get_agile_planning_sprints(self, project, team, cursor, scope):
        return self._agile_planning_page(
            "project.sprint",
            [
                ("project_id", "=", project.id),
                ("company_id", "in", [False, *self.env.companies.ids]),
                ("state", "in", ["draft", "active"]),
                ("team_id.active", "=", True),
            ]
            + ([("team_id", "=", team.id)] if team else []),
            ["name", "team_id", "state", "goal", "write_date"],
            [("state", "asc"), ("id", "desc")],
            _SPRINT_LIMIT,
            cursor,
            {**scope, "page": "sprints"},
        )

    def _agile_planning_sprint_task_domain(self, sprints, milestone=False):
        return [
            ("sprint_id", "in", sprints.ids),
            ("company_id", "in", [False, *self.env.companies.ids]),
            ("active", "=", True),
        ] + ([("milestone_id", "=", milestone.id)] if milestone else [])

    def _get_agile_planning_sprint_tasks(self, sprints, domain, cursor, scope):
        tasks, next_cursor = self._agile_planning_page(
            "project.task",
            domain,
            [
                "name",
                "agile_key",
                "agile_item_type_id",
                "agile_effective_story_points",
                "agile_backlog_sequence",
                "parent_id",
                "sprint_id",
                "agile_team_id",
                "milestone_id",
                "write_date",
            ],
            [("agile_backlog_sequence", "asc"), ("id", "asc")],
            _SPRINT_TASK_LIMIT,
            cursor,
            {**scope, "page": "tasks", "sprints": sprints.ids},
        )
        result = {sprint.id: self.env["project.task"] for sprint in sprints}
        for task in tasks:
            result[task.sprint_id.id] |= task
        return result, next_cursor

    def _get_current_sprint_points(self, domain):
        rows = self.env["project.task"]._read_group(
            domain,
            ["sprint_id"],
            ["agile_effective_story_points:sum", "__count"],
        )
        return (
            {sprint.id: points or 0.0 for sprint, points, _ in rows},
            {sprint.id: count for sprint, _, count in rows},
        )

    def _get_committed_sprint_points(self, sprints, task_domain):
        # Bind related-task visibility to the caller before aggregating history.
        # Native event rules alone do not establish visibility of each source task.
        visible_tasks = self.env["project.task"]._search(task_domain)
        # Pair each event with its Tasks current Sprint, not any loaded Sprint.
        # The window is bounded; this adds predicates, not per-Sprint queries.
        current_assignments = Domain.OR(
            Domain("sprint_id", "=", sprint.id)
            & Domain("task_id.sprint_id", "=", sprint.id)
            for sprint in sprints
        )
        rows = self.env["project.sprint.scope.event"]._read_group(
            current_assignments
            & Domain("event_type", "=", "committed")
            & Domain("task_id", "in", visible_tasks),
            ["sprint_id"],
            ["story_points:sum"],
        )
        return {sprint.id: points or 0.0 for sprint, points in rows}

    def _agile_planning_backlog_domain(self, cursor=False, team=False, milestone=False):
        self.ensure_one()
        domain = self.env["project.task"]._sprint_eligible_backlog_domain() + [
            ("project_id", "=", self.id),
            ("company_id", "in", [False, *self.env.companies.ids]),
        ]
        if team:
            domain.append(("agile_team_id", "=", team.id))
        if milestone:
            domain.append(("milestone_id", "=", milestone.id))
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

    def _get_agile_planning_backlog(self, project, cursor, team=False, milestone=False):
        tasks = self.env["project.task"].search_fetch(
            project._agile_planning_backlog_domain(cursor, team, milestone),
            [
                "name",
                "agile_key",
                "agile_item_type_id",
                "agile_effective_story_points",
                "agile_backlog_sequence",
                "parent_id",
                "sprint_id",
                "agile_team_id",
                "milestone_id",
                "write_date",
            ],
            limit=_BACKLOG_PAGE_SIZE + 1,
            order="agile_backlog_sequence, id",
        )
        visible_tasks = tasks[:_BACKLOG_PAGE_SIZE]
        has_next_page = len(tasks) > len(visible_tasks)
        next_cursor = (
            {
                "sequence": visible_tasks[-1].agile_backlog_sequence,
                "id": visible_tasks[-1].id,
                "revision": project.agile_planning_backlog_revision,
                **({"team_id": team.id} if team else {}),
                **({"milestone_id": milestone.id} if milestone else {}),
            }
            if has_next_page
            else False
        )
        return visible_tasks, next_cursor

    def _serialize_agile_planning_task(self, task, milestone_names):
        milestone_name = milestone_names.get(task.milestone_id.id)
        return {
            "id": task.id,
            "name": task.name,
            "agile_key": task.agile_key,
            "item_type": task.agile_item_type_id.display_name,
            "story_points": task.agile_effective_story_points,
            "parent": task.parent_id.display_name or None,
            "milestone": {"id": task.milestone_id.id, "name": milestone_name}
            if milestone_name
            else False,
            "version": self._agile_planning_record_version(task),
        }

    @api.model
    def apply_agile_planning_change(
        self,
        project_id,
        operation,
        task_ids,
        *,
        sprint_id=False,
        before_task_id=False,
        expected_versions=False,
        team_id=False,
        milestone_id=False,
    ):
        """Apply one current-user planning intent then return a reconciled snapshot.

        The client supplies only record identities and read versions.
        The server resolves current access, eligibility, lifecycle, and ordering.
        A shared project revision write rejects concurrent planning changes when
        the savepoint flushes, rolling back the losing intent before returning.
        """
        project = self._get_available_agile_planning_project(project_id)
        team = self._get_agile_planning_team(project, team_id)
        milestone = self._get_agile_planning_milestone(project, milestone_id)
        if operation not in {"assign", "return", "reorder"}:
            raise ValidationError(
                self.env._("Choose a valid Sprint Planning operation.")
            )
        if operation == "reorder" and milestone:
            raise ValidationError(
                self.env._("Clear the milestone filter before reordering.")
            )
        tasks = self._get_agile_planning_change_tasks(project, task_ids)
        if team and any(task.agile_team_id != team for task in tasks):
            raise ValidationError(
                self.env._("Refresh the selected team's work before changing it.")
            )
        expected_versions = self._parse_agile_planning_versions(expected_versions)
        try:
            with self.env.cr.savepoint():
                if operation == "assign":
                    self._apply_agile_planning_assignment(
                        project, tasks, sprint_id, expected_versions
                    )
                elif operation == "return":
                    self._apply_agile_planning_return(project, tasks, expected_versions)
                else:
                    self._apply_agile_planning_reorder(
                        project, tasks, before_task_id, expected_versions, team
                    )
        except (SerializationFailure, ConcurrencyError) as error:
            raise ValidationError(
                self.env._("Sprint Planning changed. Refresh and retry your action.")
            ) from error
        return self.get_agile_planning_snapshot(
            project.id, team_id=team.id or False, milestone_id=milestone.id or False
        )

    @api.model
    def _get_agile_planning_change_tasks(self, project, task_ids):
        if not isinstance(task_ids, list) or not task_ids:
            raise ValidationError(
                self.env._("Select one or more Product Backlog items.")
            )
        if len(task_ids) > _MAX_MUTATION_TASKS:
            raise ValidationError(
                self.env._("Select no more than 20 Product Backlog items.")
            )
        if any(
            not isinstance(task_id, int) or isinstance(task_id, bool) or task_id <= 0
            for task_id in task_ids
        ):
            raise ValidationError(
                self.env._("The selected Product Backlog items are invalid.")
            )
        if len(set(task_ids)) != len(task_ids):
            raise ValidationError(
                self.env._("Select each Product Backlog item only once.")
            )
        tasks = self.env["project.task"].search(
            [("id", "in", task_ids), ("project_id", "=", project.id)]
        )
        if len(tasks) != len(task_ids):
            raise AccessError(
                self.env._(
                    "One or more selected Product Backlog items are unavailable."
                )
            )
        tasks.check_access("write")
        return tasks

    @api.model
    def _parse_agile_planning_versions(self, expected_versions):
        if (
            not isinstance(expected_versions, dict)
            or set(expected_versions) != _VERSION_NAMESPACES
        ):
            raise ValidationError(
                self.env._("Refresh Sprint Planning before changing it.")
            )
        for namespace in _VERSION_NAMESPACES:
            versions = expected_versions[namespace]
            if not isinstance(versions, dict) or len(versions) > _MAX_MUTATION_TASKS:
                raise ValidationError(
                    self.env._("Refresh Sprint Planning before changing it.")
                )
            for record_id, version in versions.items():
                if (
                    not isinstance(record_id, str)
                    or not record_id.isdecimal()
                    or int(record_id) <= 0
                ):
                    raise ValidationError(
                        self.env._("Refresh Sprint Planning before changing it.")
                    )
                if not isinstance(version, str):
                    raise ValidationError(
                        self.env._("Refresh Sprint Planning before changing it.")
                    )
        return expected_versions

    @api.model
    def _agile_planning_record_version(self, record):
        write_date = fields.Datetime.to_string(record.write_date)
        if record._name == "project.task":
            return (
                f"{record.id}:{write_date}:{record.sprint_id.id or 0}:"
                f"{record.agile_backlog_sequence}:{record.name}:"
                f"{record.agile_team_id.id or 0}"
            )
        return (
            f"{record.id}:{write_date}:{record.state}:"
            f"{record.team_id.active}:{record.team_id.id}"
        )

    @api.model
    def _check_agile_planning_versions(self, records, expected_versions, namespace):
        versions = expected_versions[namespace]
        if set(versions) != {str(record.id) for record in records}:
            raise ValidationError(
                self.env._("Sprint Planning changed. Refresh and retry your action.")
            )
        for record in records:
            if versions[str(record.id)] != self._agile_planning_record_version(record):
                raise ValidationError(
                    self.env._(
                        "Sprint Planning changed. Refresh and retry your action."
                    )
                )

    @api.model
    def _increment_agile_planning_backlog_revision(self, project):
        """Invalidate cursors and serialize authorized planning changes via the ORM."""
        # Only this internal field is elevated; task mutations use the caller.
        project.sudo().write(
            {
                "agile_planning_backlog_revision": (
                    project.agile_planning_backlog_revision + 1
                )
            }
        )

    @api.model
    def _require_agile_planning_backlog_tasks(self, project, tasks):
        available = self.env["project.task"].search(
            project._agile_planning_backlog_domain() + [("id", "in", tasks.ids)]
        )
        if len(available) != len(tasks):
            raise ValidationError(
                self.env._("Only current Product Backlog items can be changed here.")
            )

    @api.model
    def _apply_agile_planning_assignment(
        self, project, tasks, sprint_id, expected_versions
    ):
        if (
            not isinstance(sprint_id, int)
            or isinstance(sprint_id, bool)
            or sprint_id <= 0
        ):
            raise ValidationError(self.env._("Choose a valid draft Sprint."))
        sprint = self.env["project.sprint"].search(
            [("id", "=", sprint_id), ("project_id", "=", project.id)], limit=1
        )
        if not sprint:
            raise AccessError(self.env._("The target Sprint is unavailable."))
        sprint.check_access("read")
        self._check_agile_planning_versions(tasks, expected_versions, "tasks")
        self._check_agile_planning_versions(sprint, expected_versions, "sprints")
        self._require_agile_planning_backlog_tasks(project, tasks)
        if not sprint.team_id.active:
            raise ValidationError(
                self.env._("The target Sprint needs an active Agile team.")
            )
        tasks.assign_product_backlog_to_sprint(sprint, draft_only=True)
        self._increment_agile_planning_backlog_revision(project)

    @api.model
    def _apply_agile_planning_return(self, project, tasks, expected_versions):
        sprints = tasks.mapped("sprint_id")
        if not sprints:
            raise ValidationError(
                self.env._("Only this project's Sprint Backlog items can be returned.")
            )
        if any(
            sprint.project_id != project or sprint.company_id != project.company_id
            for sprint in sprints
        ):
            raise ValidationError(
                self.env._("Only this project's Sprint Backlog items can be returned.")
            )
        self._check_agile_planning_versions(tasks, expected_versions, "tasks")
        self._check_agile_planning_versions(sprints, expected_versions, "sprints")
        if any(sprint.state == "closed" for sprint in sprints):
            raise ValidationError(
                self.env._("Tasks cannot be removed from a closed Sprint.")
            )
        tasks.return_sprint_tasks_to_product_backlog()
        self._increment_agile_planning_backlog_revision(project)

    @api.model
    def _apply_agile_planning_reorder(
        self, project, tasks, before_task_id, expected_versions, team=False
    ):
        if len(tasks) != 1:
            raise ValidationError(
                self.env._("Reorder one Product Backlog item at a time.")
            )
        if before_task_id is not False and (
            not isinstance(before_task_id, int)
            or isinstance(before_task_id, bool)
            or before_task_id <= 0
        ):
            raise ValidationError(
                self.env._("The Product Backlog ordering target is invalid.")
            )
        task = tasks
        domain = project._agile_planning_backlog_domain(team=team) + [
            ("id", "!=", task.id)
        ]
        before_task = self.env["project.task"]
        if before_task_id:
            before_task = self.env["project.task"].search(
                domain + [("id", "=", before_task_id)], limit=1
            )
            if not before_task:
                raise AccessError(
                    self.env._("The Product Backlog ordering target is unavailable.")
                )
            previous_task = self.env["project.task"].search(
                domain
                + [
                    "|",
                    ("agile_backlog_sequence", "<", before_task.agile_backlog_sequence),
                    "&",
                    ("agile_backlog_sequence", "=", before_task.agile_backlog_sequence),
                    ("id", "<", before_task.id),
                ],
                order="agile_backlog_sequence desc, id desc",
                limit=1,
            )
        else:
            previous_task = self.env["project.task"].search(
                domain, order="agile_backlog_sequence desc, id desc", limit=1
            )
        self._require_agile_planning_backlog_tasks(project, task)
        self._check_agile_planning_versions(
            task | before_task, expected_versions, "tasks"
        )
        if before_task:
            new_sequence = (
                (
                    previous_task.agile_backlog_sequence
                    + before_task.agile_backlog_sequence
                )
                // 2
                if previous_task
                else before_task.agile_backlog_sequence - 10
            )
            if previous_task and new_sequence in {
                previous_task.agile_backlog_sequence,
                before_task.agile_backlog_sequence,
            }:
                new_sequence = before_task.agile_backlog_sequence - 1
        elif previous_task:
            new_sequence = previous_task.agile_backlog_sequence + 10
        else:
            return
        if task.agile_backlog_sequence == new_sequence:
            return
        task.write({"agile_backlog_sequence": new_sequence})
        self._increment_agile_planning_backlog_revision(project)

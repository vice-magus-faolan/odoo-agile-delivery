"""Caller-visible terminal work, independent of native closed-child counters."""

from collections import deque

from odoo import api, fields, models


class ProjectTask(models.Model):
    # Read-only progress aggregation is separate from task lifecycle guards.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "project.task"

    agile_progress = fields.Json(compute="_compute_agile_progress", compute_sudo=False)
    agile_progress_items = fields.Char(
        compute="_compute_agile_progress",
        compute_sudo=False,
        string="Completed / total items",
    )
    agile_progress_points = fields.Char(
        compute="_compute_agile_progress",
        compute_sudo=False,
        string="Completed / total story points",
    )
    agile_progress_root_id = fields.Many2one(
        "project.task",
        compute="_compute_agile_progress_root",
        search="_search_agile_progress_root",
        string="Contributing to",
    )

    def _agile_progress_forest(self):
        """Fetch once as the caller; missing intermediate nodes break a branch."""
        self = self.filtered(lambda task: isinstance(task.id, int))
        if not self:
            return {}, {}
        self.check_access("read")
        projects = self.env["project.project"].search(
            [
                ("id", "in", self.project_id.ids),
                ("agile_enabled", "=", True),
                ("active", "=", True),
                ("is_template", "=", False),
            ]
        )
        tasks = self.with_context(active_test=True).search_fetch(
            [
                ("id", "child_of", self.ids),
                ("project_id", "in", projects.ids),
                ("active", "=", True),
                ("state", "!=", "1_canceled"),
                ("has_template_ancestor", "=", False),
                ("has_project_template", "=", False),
            ],
            [
                "parent_id",
                "project_id",
                "state",
                "agile_item_type_id",
                "agile_uses_story_points",
                "agile_effective_story_points",
            ],
        )
        by_id = {task.id: task for task in tasks}
        children = {task.id: [] for task in tasks}
        for task in tasks:
            parent = by_id.get(task.parent_id.id)
            if parent and parent.project_id == task.project_id:
                children[parent.id].append(task.id)
        return by_id, children

    @api.model
    def _agile_leaf_progress(self, task):
        points_work = task.project_id.agile_estimation_method == "fibonacci" and (
            not task.agile_item_type_id or task.agile_uses_story_points
        )
        points = task.agile_effective_story_points if points_work else 0
        done = task.state == "1_done"
        return {
            "items": 1,
            "done": int(done),
            "points": points,
            "done_points": points if done else 0,
            "point_items": int(points_work),
            "unestimated": int(points_work and not points),
        }

    @api.depends(
        "project_id",
        "project_id.active",
        "project_id.agile_enabled",
        "project_id.agile_estimation_method",
        "project_id.task_ids",
        "project_id.task_ids.parent_id",
        "project_id.task_ids.state",
        "project_id.task_ids.active",
        "project_id.task_ids.has_template_ancestor",
        "project_id.task_ids.has_project_template",
        "project_id.task_ids.agile_item_type_id",
        "project_id.task_ids.agile_uses_story_points",
        "project_id.task_ids.agile_effective_story_points",
    )
    @api.depends_context("uid", "company")
    def _compute_agile_progress(self):
        # Project-scoped dependencies invalidate even uncomputed intermediate
        # ancestors. Recursive fields would force a query per requested root.
        by_id, children = self._agile_progress_forest()
        empty = dict.fromkeys(
            ["items", "done", "points", "done_points", "point_items", "unestimated"], 0
        )
        parents = {
            child_id: parent_id
            for parent_id, ids in children.items()
            for child_id in ids
        }
        remaining = {task_id: len(ids) for task_id, ids in children.items()}
        queue = deque(task_id for task_id, count in remaining.items() if not count)
        totals = {task_id: dict(empty) for task_id in by_id}
        for task_id in queue:
            totals[task_id] = self._agile_leaf_progress(by_id[task_id])
        while queue:
            task_id = queue.popleft()
            parent_id = parents.get(task_id)
            if parent_id is None:
                continue
            for key, value in totals[task_id].items():
                totals[parent_id][key] += value
            remaining[parent_id] -= 1
            if not remaining[parent_id]:
                queue.append(parent_id)
        for task in self:
            progress = totals[task.id] if children.get(task.id) else dict(empty)
            task.agile_progress = progress
            task.agile_progress_items = (
                self.env._(
                    "%(done)s / %(total)s items",
                    done=progress["done"],
                    total=progress["items"],
                )
                if progress["items"]
                else self.env._("No contributing work")
            )
            task.agile_progress_points = self._agile_progress_point_label(progress)

    @api.model
    def _agile_progress_point_label(self, progress):
        if not progress["point_items"]:
            return self.env._("No story-point work")
        label = self.env._(
            "%(done)g / %(total)g known points",
            done=progress["done_points"],
            total=progress["points"],
        )
        if progress["unestimated"]:
            return self.env._(
                "%(points)s; %(count)s unestimated",
                points=label,
                count=progress["unestimated"],
            )
        return label

    def _agile_progress_leaf_ids(self):
        """Resolve the same terminal frontier again on every drilldown search."""
        _by_id, children = self._agile_progress_forest()
        pending = [child_id for root in self for child_id in children.get(root.id, [])]
        visited = set()
        leaves = set()
        while pending:
            task_id = pending.pop()
            if task_id in visited:
                continue
            visited.add(task_id)
            if children[task_id]:
                pending.extend(children[task_id])
            else:
                leaves.add(task_id)
        return list(leaves)

    def _compute_agile_progress_root(self):
        for task in self:
            task.agile_progress_root_id = False

    @api.model
    def _search_agile_progress_root(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        leaves = self.browse(value)._agile_progress_leaf_ids()
        return [("id", operator, leaves)]

    def action_agile_progress_work(self):
        """Open a live caller-resolved native work list, not a frozen ID page."""
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Contributing work"),
            "res_model": "project.task",
            "view_mode": "list,form",
            "views": [
                (
                    self.env.ref("project_agile.view_task_list_agile_progress").id,
                    "list",
                ),
                (False, "form"),
            ],
            "domain": [("agile_progress_root_id", "=", self.id)],
            "context": {"create": False, "active_test": True, "group_by": []},
        }

from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import AccessError
from odoo.tools.float_utils import float_round


class ProjectScrumAnalytics(models.AbstractModel):
    """Build deterministic Sprint analytics from immutable scope events."""

    _name = "project.scrum.analytics"
    _description = "Scrum Analytics Calculation Service"

    _POINT_PRECISION = 2

    @api.model
    def get_report(self, sprint_id):
        """Return the authorized Sprint report replayed from immutable facts only."""
        sprint = self._get_authorized_sprint(sprint_id)
        replay = self._replay_sprint(sprint)
        return self._present_report(sprint, replay)

    def _get_authorized_sprint(self, sprint_id):
        if not isinstance(sprint_id, int) or isinstance(sprint_id, bool):
            raise AccessError(_("A valid Sprint identifier is required."))
        sprint = self.env["project.sprint"].browse(sprint_id).exists()
        if not sprint:
            raise AccessError(_("The requested Sprint is not available."))
        sprint.check_access("read")
        if sprint.company_id and sprint.company_id not in self.env.companies:
            raise AccessError(_("The requested Sprint belongs to an unavailable company."))
        sprint.project_id.check_access("read")
        return sprint

    def _replay_sprint(self, sprint):
        boundary = sprint.closed_at if sprint.state == "closed" and sprint.closed_at else False
        domain = [("sprint_id", "=", sprint.id)]
        if boundary:
            domain.append(("event_at", "<=", boundary))
        events = self.env["project.sprint.scope.event"].search(domain, order="event_at, id")
        task_states = defaultdict(lambda: {"in_scope": False, "done": False, "points": 0.0})
        committed_points = {}
        scope_change = {"initial": 0.0, "added": 0.0, "removed": 0.0}
        timeline = []
        event_handlers = self._event_handlers()
        for event in events:
            task_state = task_states[event.task_id.id]
            event_handlers[event.event_type](
                event, task_state, committed_points, scope_change
            )
            timeline.append(self._timeline_point(event, task_states))
        return {
            "as_of": boundary or (events[-1:].event_at if events else False),
            "committed_points": committed_points,
            "scope_change": scope_change,
            "task_states": task_states,
            "timeline": timeline,
            "precision": "trusted" if boundary else "active_or_legacy",
        }

    def _event_handlers(self):
        """Keep ADR-009 event semantics explicit and independently auditable."""
        return {
            "committed": self._apply_committed,
            "added": self._apply_added,
            "removed": self._apply_removed,
            "reestimated": self._apply_reestimated,
            "completed": self._apply_completed,
            "reopened": self._apply_reopened,
            "carried_to_backlog": self._apply_carry_over,
            "carried_to_sprint": self._apply_carry_over,
        }

    def _apply_committed(self, event, task_state, committed_points, scope_change):
        task_state.update(in_scope=True, points=event.story_points)
        committed_points[event.task_id.id] = event.story_points
        scope_change["initial"] += event.story_points

    def _apply_added(self, event, task_state, _committed_points, scope_change):
        task_state.update(in_scope=True, points=event.story_points)
        scope_change["added"] += event.story_points

    def _apply_removed(self, event, task_state, _committed_points, scope_change):
        task_state["in_scope"] = False
        scope_change["removed"] += event.story_points

    def _apply_reestimated(self, event, task_state, _committed_points, _scope_change):
        task_state["points"] = event.story_points

    def _apply_completed(self, _event, task_state, _committed_points, _scope_change):
        task_state["done"] = True

    def _apply_reopened(self, _event, task_state, _committed_points, _scope_change):
        task_state["done"] = False

    def _apply_carry_over(self, _event, task_state, _committed_points, _scope_change):
        task_state["in_scope"] = False

    def _timeline_point(self, event, task_states):
        metrics = self._raw_metrics(task_states)
        return {
            "event_at": event.event_at,
            "event_id": event.id,
            "burndown_remaining": metrics["remaining"],
            "burnup_completed": metrics["completed"],
            "burnup_total": metrics["total"],
        }

    def _raw_metrics(self, task_states):
        in_scope = [state for state in task_states.values() if state["in_scope"]]
        return {
            "remaining": sum(state["points"] for state in in_scope if not state["done"]),
            "completed": sum(state["points"] for state in in_scope if state["done"]),
            "total": sum(state["points"] for state in in_scope),
        }

    def _present_report(self, sprint, replay):
        metrics = self._raw_metrics(replay["task_states"])
        committed_completion = sum(
            points
            for task_id, points in replay["committed_points"].items()
            if replay["task_states"][task_id]["done"]
        )
        commitment = replay["scope_change"]["initial"]
        ratio = committed_completion / commitment if commitment else 0.0
        velocity = metrics["completed"] if sprint.state == "closed" else 0.0
        return {
            "sprint": {
                "id": sprint.id,
                "state": sprint.state,
                "as_of": replay["as_of"],
                "precision": replay["precision"],
            },
            "units": {"points": "story_points", "completion_ratio": "fraction"},
            "velocity": self._round(velocity),
            "burndown": {"remaining": self._round(metrics["remaining"])},
            "burnup": {
                "completed": self._round(metrics["completed"]),
                "total": self._round(metrics["total"]),
            },
            "scope_change": {
                "initial": self._round(replay["scope_change"]["initial"]),
                "added": self._round(replay["scope_change"]["added"]),
                "removed": self._round(replay["scope_change"]["removed"]),
                "final": self._round(metrics["total"]),
            },
            "commitment_completion": {
                "commitment": self._round(commitment),
                "completed": self._round(committed_completion),
                "completion_ratio": self._round(ratio),
            },
            "timeline": [
                {
                    **point,
                    "burndown_remaining": self._round(point["burndown_remaining"]),
                    "burnup_completed": self._round(point["burnup_completed"]),
                    "burnup_total": self._round(point["burnup_total"]),
                }
                for point in replay["timeline"]
            ],
        }

    def _round(self, value):
        return float_round(value, precision_digits=self._POINT_PRECISION)

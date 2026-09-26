from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ProjectScrumAnalyticsAccess(models.AbstractModel):
    """Apply native project visibility to stored analytics records."""

    _name = "project.scrum.analytics.access"
    _description = "Scrum Analytics Project Access"

    def _analytics_project_domain(self):
        projects = self.env["project.project"].search([])
        return [("project_id", "in", projects.ids)]

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        domain = fields.Domain.AND(
            [fields.Domain(domain), fields.Domain(self._analytics_project_domain())]
        )
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            active_test=active_test,
            bypass_access=bypass_access,
        )

    def check_access(self, operation):
        result = super().check_access(operation)
        if operation == "read" and self and not self.env.is_superuser():
            permitted_project_ids = set(self.env["project.project"].search([]).ids)
            if not set(self.project_id.ids).issubset(permitted_project_ids):
                raise AccessError(_("The requested analytics records are not available."))
        return result


class ProjectScrumAnalyticsReport(models.Model):
    """One stored, access-controlled analytics record per Agile Sprint."""

    _name = "project.scrum.analytics.report"
    _inherit = "project.scrum.analytics.access"
    _description = "Scrum Sprint Analytics"
    _rec_name = "sprint_id"
    _order = "closed_at desc, sprint_id desc"

    sprint_id = fields.Many2one("project.sprint", required=True, readonly=True, ondelete="cascade", index=True)
    project_id = fields.Many2one(related="sprint_id.project_id", store=True, readonly=True, index=True)
    company_id = fields.Many2one(related="sprint_id.company_id", store=True, readonly=True, index=True)
    team_id = fields.Many2one(related="sprint_id.team_id", store=True, readonly=True, index=True)
    state = fields.Selection(related="sprint_id.state", store=True, readonly=True, index=True)
    date_start = fields.Date(related="sprint_id.date_start", store=True, readonly=True, index=True)
    date_end = fields.Date(related="sprint_id.date_end", store=True, readonly=True, index=True)
    closed_at = fields.Datetime(related="sprint_id.closed_at", store=True, readonly=True, index=True)
    precision = fields.Selection(
        [("trusted", "Trusted closed-Sprint replay"), ("active_or_legacy", "Active or legacy replay")],
        compute="_compute_precision",
        store=True,
        readonly=True,
        help="Closed Sprints with a close timestamp are replayed to that immutable boundary.",
    )
    points_unit = fields.Selection(
        [("story_points", "Story Points")],
        default="story_points",
        readonly=True,
        required=True,
    )
    completion_ratio_unit = fields.Selection(
        [("fraction", "Fraction")],
        default="fraction",
        readonly=True,
        required=True,
    )
    velocity = fields.Float(
        string="Velocity (Closed Sprint, Story Points)",
        compute="_compute_velocity",
        store=True,
        readonly=True,
    )
    burndown_remaining = fields.Float(string="Burndown Remaining (Story Points)", readonly=True)
    burnup_completed = fields.Float(string="Burnup Completed (Story Points)", readonly=True)
    burnup_total = fields.Float(string="Burnup Total (Story Points)", readonly=True)
    scope_initial = fields.Float(string="Initial Scope (Story Points)", readonly=True)
    scope_added = fields.Float(string="Scope Added (Story Points)", readonly=True)
    scope_removed = fields.Float(string="Scope Removed (Story Points)", readonly=True)
    scope_final = fields.Float(string="Final Scope (Story Points)", readonly=True)
    commitment_points = fields.Float(string="Original Commitment (Story Points)", readonly=True)
    completed_commitment_points = fields.Float(
        string="Completed Commitment (Story Points)", readonly=True
    )
    commitment_completion_ratio = fields.Float(
        string="Commitment Completion (Fraction)", readonly=True, aggregator="avg"
    )

    _sprint_unique = models.Constraint(
        "UNIQUE(sprint_id)", "Each Sprint has one analytics report."
    )

    @api.depends("state", "closed_at")
    def _compute_precision(self):
        for report in self:
            report.precision = (
                "trusted" if report.state == "closed" and report.closed_at else "active_or_legacy"
            )

    @api.depends("state", "burnup_completed")
    def _compute_velocity(self):
        for report in self:
            report.velocity = report.burnup_completed if report.state == "closed" else 0.0

    @api.model
    def _ensure_all_sprints(self):
        self._sync_sprints(self.env["project.sprint"].search([]))

    @api.model
    def _sync_sprints(self, sprints):
        """Synchronize trusted stored projections after immutable facts change."""
        if not self.env.is_superuser():
            raise AccessError(_("Analytics projections are maintained by the system."))
        sprints = sprints.exists()
        if not sprints:
            return
        reports = self._ensure_reports(sprints)
        reports_by_sprint = {report.sprint_id.id: report for report in reports}
        analytics = self.env["project.scrum.analytics"]
        for sprint in sprints:
            report_data = analytics.get_report(sprint.id)
            report = reports_by_sprint[sprint.id]
            report.write(self._report_values(report_data))
            report._sync_timeline(report_data["timeline"])

    @api.model
    def _ensure_reports(self, sprints):
        existing = self.search([("sprint_id", "in", sprints.ids)])
        existing_sprint_ids = set(existing.sprint_id.ids)
        missing_sprints = sprints.filtered(lambda sprint: sprint.id not in existing_sprint_ids)
        if missing_sprints:
            existing |= self.create([{"sprint_id": sprint.id} for sprint in missing_sprints])
        return existing

    def _report_values(self, report_data):
        return {
            "burndown_remaining": report_data["burndown"]["remaining"],
            "burnup_completed": report_data["burnup"]["completed"],
            "burnup_total": report_data["burnup"]["total"],
            "scope_initial": report_data["scope_change"]["initial"],
            "scope_added": report_data["scope_change"]["added"],
            "scope_removed": report_data["scope_change"]["removed"],
            "scope_final": report_data["scope_change"]["final"],
            "commitment_points": report_data["commitment_completion"]["commitment"],
            "completed_commitment_points": report_data["commitment_completion"]["completed"],
            "commitment_completion_ratio": report_data["commitment_completion"]["completion_ratio"],
        }

    def _sync_timeline(self, timeline):
        self.ensure_one()
        lines = self.env["project.scrum.analytics.timeline"].search(
            [("report_id", "=", self.id)]
        )
        lines_by_event = {line.scope_event_id.id: line for line in lines}
        timeline_event_ids = set()
        for point in timeline:
            timeline_event_ids.add(point["event_id"])
            values = {
                "report_id": self.id,
                "scope_event_id": point["event_id"],
                "event_at": point["event_at"],
                "burndown_remaining": point["burndown_remaining"],
                "burnup_completed": point["burnup_completed"],
                "burnup_total": point["burnup_total"],
            }
            line = lines_by_event.get(point["event_id"])
            if line:
                line.write(values)
            else:
                self.env["project.scrum.analytics.timeline"].create(values)
        lines.filtered(lambda line: line.scope_event_id.id not in timeline_event_ids).unlink()

    def _check_report_read_access(self):
        self.ensure_one()
        self.check_access("read")
        self.env["project.scrum.analytics"].get_report(self.sprint_id.id)

    def action_open_sprint(self):
        self._check_report_read_access()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sprint"),
            "res_model": "project.sprint",
            "view_mode": "form",
            "res_id": self.sprint_id.id,
            "target": "current",
        }

    def action_open_timeline(self):
        self._check_report_read_access()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sprint Analytics Timeline"),
            "res_model": "project.scrum.analytics.timeline",
            "view_mode": "list,pivot,graph,form",
            "domain": [("report_id", "=", self.id)],
            "context": {"default_report_id": self.id},
        }


class ProjectScrumAnalyticsTimeline(models.Model):
    """Stored event-level Burndown and Burnup points for native charts."""

    _name = "project.scrum.analytics.timeline"
    _inherit = "project.scrum.analytics.access"
    _description = "Scrum Analytics Timeline"
    _order = "event_at, id"

    report_id = fields.Many2one("project.scrum.analytics.report", required=True, readonly=True, ondelete="cascade", index=True)
    scope_event_id = fields.Many2one("project.sprint.scope.event", required=True, readonly=True, ondelete="cascade", index=True)
    project_id = fields.Many2one(related="report_id.project_id", store=True, readonly=True, index=True)
    company_id = fields.Many2one(related="report_id.company_id", store=True, readonly=True, index=True)
    sprint_id = fields.Many2one(related="report_id.sprint_id", store=True, readonly=True, index=True)
    team_id = fields.Many2one(related="report_id.team_id", store=True, readonly=True, index=True)
    state = fields.Selection(related="report_id.state", store=True, readonly=True, index=True)
    task_id = fields.Many2one(related="scope_event_id.task_id", store=True, readonly=True, index=True)
    event_type = fields.Selection(related="scope_event_id.event_type", store=True, readonly=True, index=True)
    event_at = fields.Datetime(
        string="Event Timestamp (UTC; chart buckets use your timezone)",
        readonly=True,
        index=True,
    )
    burndown_remaining = fields.Float(string="Burndown Remaining (Story Points)", readonly=True)
    burnup_completed = fields.Float(string="Burnup Completed (Story Points)", readonly=True)
    burnup_total = fields.Float(string="Burnup Total (Story Points)", readonly=True)

    _scope_event_unique = models.Constraint(
        "UNIQUE(scope_event_id)", "Each scope event has one analytics timeline point."
    )

    def action_open_task(self):
        self.ensure_one()
        self.report_id._check_report_read_access()
        self.task_id.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": _("Task"),
            "res_model": "project.task",
            "view_mode": "form",
            "res_id": self.task_id.id,
            "target": "current",
        }


class ProjectSprint(models.Model):
    """Create an additive analytics projection without changing Scrum behavior."""

    _inherit = "project.sprint"

    @api.model_create_multi
    def create(self, vals_list):
        sprints = super().create(vals_list)
        self.env["project.scrum.analytics.report"].sudo()._sync_sprints(sprints)
        return sprints

    def write(self, values):
        """Rebuild projections after a supported close-time recovery correction."""
        result = super().write(values)
        if "closed_at" in values:
            self.env["project.scrum.analytics.report"].sudo()._sync_sprints(self)
        return result


class ProjectSprintScopeEvent(models.Model):
    """Keep the stored reporting projection aligned with immutable event facts."""

    _inherit = "project.sprint.scope.event"

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        self.env["project.scrum.analytics.report"].sudo()._sync_sprints(events.sprint_id)
        return events

    def write(self, values):
        sprints = self.sprint_id
        result = super().write(values)
        self.env["project.scrum.analytics.report"].sudo()._sync_sprints(sprints | self.sprint_id)
        return result

    def unlink(self):
        sprints = self.sprint_id
        result = super().unlink()
        self.env["project.scrum.analytics.report"].sudo()._sync_sprints(sprints)
        return result

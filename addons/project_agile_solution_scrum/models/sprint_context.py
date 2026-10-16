"""Optional immutable actual requirement context for native scope events."""

import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from odoo.addons.project_agile_solution.models.solution_task_access import (
    check_document,
    check_task,
)


class SprintRequirementContext(models.Model):
    _name = "project.agile.solution.sprint.context"
    _inherit = "project.agile.solution.task.access"
    _description = "Frozen Exact Requirement at Native Sprint Event"
    _check_company_auto = True
    _rec_name = "requirement_revision_id"

    scope_event_id = fields.Many2one(
        "project.sprint.scope.event", required=True, ondelete="restrict", index=True
    )
    task_id = fields.Many2one(
        "project.task",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    requirement_revision_id = fields.Many2one(
        "project.agile.requirement.revision",
        required=True,
        ondelete="restrict",
        check_company=True,
    )
    solution_id = fields.Many2one(
        related="requirement_revision_id.solution_id", store=True
    )
    document_revision_id = fields.Many2one(
        "project.agile.solution.revision", ondelete="restrict", check_company=True
    )
    _payload = fields.Text(
        required=True, groups="project_agile_solution.group_snapshot_storage"
    )
    payload_json = fields.Text(compute="_compute_payload", compute_sudo=False)
    _event_edge_unique = models.Constraint(
        "UNIQUE(scope_event_id, requirement_revision_id)",
        "Exact context was already captured for this event.",
    )

    def _search_native_project_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        events = self.env["project.sprint.scope.event"].sudo(False)
        accessible = Domain.AND(
            [
                self._reference_access_domain(),
                Domain("scope_event_id", "in", events._search([])),
            ]
        )
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    def _reference_access_domain(self):
        """Acyclic exact-reference closure shared with native event visibility."""
        domains = []
        for field, model in (
            ("task_id", "project.task"),
            ("requirement_revision_id", "project.agile.requirement.revision"),
            ("solution_id", "project.agile.solution"),
        ):
            domains.append(
                Domain(
                    field,
                    "in",
                    self.env[model]
                    .sudo(False)
                    .with_context(active_test=False)
                    ._search([]),
                )
            )
        documents = (
            self.env["project.agile.solution.revision"]
            .sudo(False)
            .with_context(active_test=False)
        )
        domains.append(
            Domain.OR(
                [
                    Domain("document_revision_id", "=", False),
                    Domain("document_revision_id", "in", documents._search([])),
                ]
            )
        )
        return Domain.AND(domains)

    @api.model
    # Captured history has no caller-provided defaults, even through Form/RPC.
    def default_get(self, names):  # pylint: disable=method-required-super
        return {}

    @api.model_create_multi
    # Only private native event capture can create immutable context.
    def create(self, vals_list):  # pylint: disable=method-required-super
        raise AccessError(
            _(
                "Requirement Sprint context is created only "
                "by native scope event capture."
            )
        )

    # Captured context cannot be rewritten.
    def write(self, values):  # pylint: disable=method-required-super
        raise ValidationError(_("Captured requirement context is immutable."))

    # Native scope history requires retained context, not deletion.
    def unlink(self):  # pylint: disable=method-required-super
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("Captured requirement context must be retained."))

    # Copy/backfill cannot substitute for observed native scope capture.
    def copy(self, default=None):  # pylint: disable=method-required-super
        raise ValidationError(_("Captured context cannot be copied or backfilled."))

    @api.depends_context("uid")
    def _compute_payload(self):
        for record in self:
            caller = record.sudo(False)
            caller.check_access("read")
            caller.scope_event_id.check_access("read")
            caller.requirement_revision_id._check_snapshot_reference({})
            check_document(
                caller.document_revision_id,
                caller.requirement_revision_id,
                caller.solution_id,
            )
            caller.payload_json = caller.sudo()._payload

    def _capture(self, event, links):
        """Already-authorized, locked current links only; no public dispatch seam."""
        values = []
        for link in links:
            revision = link.requirement_revision_id.sudo(False)
            revision._check_snapshot_reference({})
            if not revision.sealed:
                raise ValidationError(
                    _("Linked requirement content must already be sealed.")
                )
            document = link.document_revision_id.sudo(False)
            check_document(document, revision, link.solution_id)
            payload = {
                "requirement": revision._snapshot_values(),
                "specification": {
                    "id": document.id,
                    "number": document.number,
                    "state": document.state,
                }
                if document
                else None,
            }
            values.append(
                {
                    "scope_event_id": event.id,
                    "task_id": event.task_id.id,
                    "requirement_revision_id": revision.id,
                    "document_revision_id": document.id or False,
                    "_payload": json.dumps(payload, sort_keys=True, default=str),
                }
            )
        return super(SprintRequirementContext, self.sudo()).create(values)


class ScopeEventTrace(models.Model):
    _inherit = "project.sprint.scope.event"

    solution_capture_status = fields.Selection(
        [
            ("not_available", "Not Available / Predates Bridge"),
            ("captured", "Exact Context Captured"),
            ("empty", "No Active Requirement Links"),
        ],
        default="not_available",
        required=True,
        readonly=True,
        copy=False,
    )
    solution_context_ids = fields.One2many(
        "project.agile.solution.sprint.context",
        "scope_event_id",
        readonly=True,
        copy=False,
        groups="project_agile_solution.group_snapshot_storage",
    )
    solution_native_access = fields.Boolean(
        search="_search_solution_native_access",
        compute="_compute_solution_native_access",
    )

    def _compute_solution_native_access(self):
        for event in self:
            event.solution_native_access = True

    def _search_solution_native_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        tasks = self.env["project.task"].sudo(False).with_context(active_test=False)
        contexts = self.env["project.agile.solution.sprint.context"].sudo(False)
        sprints = self.env["project.sprint"].sudo(False).with_context(active_test=False)
        accessible = Domain.AND(
            [
                Domain("task_id", "in", tasks._search([])),
                Domain("sprint_id", "in", sprints._search([])),
                # Never recurse context -> event -> context. Explicit caller-bound
                # reference subqueries still enforce hidden requirements/specs.
                Domain(
                    "solution_context_ids",
                    "not any",
                    ~contexts._reference_access_domain(),
                ),
            ]
        )
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    @api.model
    def default_get(self, names):
        values = super().default_get(
            [
                name
                for name in names
                if name not in {"solution_capture_status", "solution_context_ids"}
            ]
        )
        return {
            key: value
            for key, value in values.items()
            if key not in {"solution_capture_status", "solution_context_ids"}
        }

    @api.model_create_multi
    def create(self, vals_list):
        if any(
            {"solution_capture_status", "solution_context_ids"} & values.keys()
            for values in vals_list
        ):
            raise ValidationError(_("Scope capture proof is not caller supplied."))
        return super().create(
            [
                {**values, "solution_capture_status": "not_available"}
                for values in vals_list
            ]
        )

    def write(self, values):
        if {"solution_capture_status", "solution_context_ids"} & values.keys():
            raise ValidationError(_("Scope capture proof is immutable."))
        return super().write(values)

    def action_open_solution_context(self):
        self.ensure_one()
        self.sudo(False).check_access("read")
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.agile.solution.sprint.context",
            "view_mode": "list,form",
            "domain": [("scope_event_id", "=", self.id)],
        }

    def _mark_capture(self, status):
        if any(event.solution_capture_status != "not_available" for event in self):
            raise ValidationError(_("Historical context cannot be recaptured."))
        return super(ScopeEventTrace, self.sudo()).write(
            {"solution_capture_status": status}
        )


class SprintTrace(models.Model):
    _inherit = "project.sprint"

    def _append_scope_events(self, event_type, tasks, **kwargs):
        """Delegate all native event values and lifecycle semantics unchanged."""
        self.ensure_one()
        caller = self.sudo(False)
        caller.check_access("read")
        # Ordinary authorized Task completion must not require Solution Manager
        # privileges. Link creation already sealed content; capture is read-only.
        tasks = tasks.sudo(False)
        for task in tasks:
            check_task(task, caller.project_id, active=False)
        links_model = self.env["project.agile.requirement.task.link"].sudo(False)
        tasks.lock_for_update(allow_referencing=True)
        # Re-read under shared Task locks. Private boolean completeness only;
        # inaccessible links cannot be silently omitted and labelled empty.
        links = links_model.search([("task_id", "in", tasks.ids)])
        total = links_model.sudo().search_count([("task_id", "in", tasks.ids)])
        if total != len(links):
            raise AccessError(
                _("Exact requirement context is unavailable under current access.")
            )
        with self.env.cr.savepoint():
            events = super()._append_scope_events(event_type, tasks, **kwargs)
            for event in events:
                # filtered consumes this predicate before the next event.
                current = links.filtered(
                    lambda link: link.task_id == event.task_id  # noqa: B023
                )
                self.env["project.agile.solution.sprint.context"]._capture(
                    event, current
                )
                event._mark_capture("captured" if current else "empty")
            return events

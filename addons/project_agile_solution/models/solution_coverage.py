"""Bounded honest internal coverage categories; never infer acceptance from work."""

import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

LIMIT = 1000


def complete_rows(env, model, domain):
    """Narrow elevated cardinality is a deny guard, never returned metadata."""
    caller = env[model].sudo(False).with_context(active_test=False)
    rows = caller.search(domain, limit=LIMIT + 1)
    if len(rows) > LIMIT:
        raise ValidationError(
            _("Selected scope exceeds the bounded preview; split the initiative.")
        )
    if caller.sudo().search_count(domain, limit=LIMIT + 1) != len(rows):
        raise AccessError(
            _("Coverage is unavailable because required scope is inaccessible.")
        )
    rows.check_access("read")
    return rows


def requirement_label(row):
    row.requirement_id.sudo(False).check_access("read")
    return {"key": row.requirement_id.key, "number": row.number, "title": row.title}


def task_label(row):
    row.sudo(False).check_access("read")
    return {"key": row.agile_key, "title": row.name, "archived": not row.active}


class SolutionCoverage(models.Model):
    _inherit = "project.agile.solution.revision"

    def action_coverage(self, baseline_id=None):
        """Requery exact selected content and all scoped work before classifying."""
        payload = self._render_payload()
        caller = self.sudo(False).with_context(active_test=False)
        baseline_payload = caller._coverage_baseline(baseline_id)
        scope = [("solution_id", "=", caller.solution_id.id)]
        heads = caller._coverage_heads(scope)
        links = complete_rows(
            caller.env,
            "project.agile.requirement.task.link",
            scope + [("active", "=", True)],
        )
        tasks = complete_rows(
            caller.env,
            "project.task",
            [
                ("project_id", "=", caller.project_id.id),
                ("agile_item_type_id", "!=", False),
            ],
        )
        events = complete_rows(
            caller.env, "project.agile.requirement.acceptance", scope
        )
        selected = caller.requirement_revision_ids.sudo(False)
        selected.check_access("read")
        linked_ids = set(links.requirement_revision_id.ids)
        linked_tasks = set(links.task_id.ids)
        categories = {
            "unlinked_requirements": [
                requirement_label(row) for row in selected if row.id not in linked_ids
            ],
            "linked_exact_requirements": [
                requirement_label(row) for row in selected if row.id in linked_ids
            ],
            "older_revision_work": [
                dict(
                    task_label(edge.task_id),
                    requirement=requirement_label(edge.requirement_revision_id),
                )
                for edge in links
                if heads[edge.requirement_revision_id.requirement_id.id]
                != edge.requirement_revision_id.id
            ],
            **caller._coverage_work(tasks, linked_tasks),
            "unresolved_questions_affecting_work": caller._coverage_questions(),
            **caller._coverage_acceptance(selected, events),
            **caller._coverage_portal(events),
            "changes_since_baseline": caller._coverage_changes(
                payload, baseline_payload
            ),
        }
        return {
            "notice": _(
                "Internal checked scope only; project-wide native work may serve "
                "other initiatives. No completion percentage. "
                "Task Done/PR merge is not acceptance."
            ),
            "selected_revision": caller.number,
            "selected_status": caller.state,
            "baseline_revision": baseline_payload["number"]
            if baseline_payload
            else None,
            "categories": categories,
        }

    def _coverage_work(self, tasks, linked_tasks):
        categories = {
            "legitimate_unlinked_maintenance": [],
            "unexplained_unlinked_work": [],
        }
        for task in tasks:
            if task.id in linked_tasks:
                continue
            reason = (task.solution_maintenance_reason or "").strip()
            if reason:
                categories["legitimate_unlinked_maintenance"].append(
                    dict(task_label(task), reason=reason)
                )
            else:
                categories["unexplained_unlinked_work"].append(task_label(task))
        return categories

    def _coverage_baseline(self, baseline_id):
        if baseline_id is None or baseline_id is False:
            return None
        baseline = self._checked_relation(self._name, baseline_id)
        if (
            baseline.document_id != self.document_id
            or baseline.state not in ("approved", "superseded")
            or baseline.number > self.number
        ):
            raise ValidationError(
                _(
                    "Compare an exact approved baseline of this document, "
                    "not a different scope or future revision."
                )
            )
        return baseline._render_payload()

    def _coverage_heads(self, scope):
        identities = complete_rows(self.env, "project.agile.requirement", scope)
        revisions = complete_rows(self.env, "project.agile.requirement.revision", scope)
        identities.check_access("read")
        heads = {}
        for revision in revisions.sorted("number"):
            revision.requirement_id.check_access("read")
            heads[revision.requirement_id.id] = revision.id
        return heads

    def _coverage_questions(self):
        questions = self.context_revision_ids.sudo(False).filtered(
            lambda row: row.kind == "question"
            and row.resolution_status == "open"
            and row.planning_significance in ("planning", "blocking")
        )
        questions._validate_content()
        return [
            {
                "title": row.title,
                "significance": row.planning_significance,
                "requirements": [
                    requirement_label(item)
                    for item in row.affected_requirement_revision_ids
                ],
                "discovery_work": [task_label(item) for item in row.spike_task_ids],
            }
            for row in questions
        ]

    def _coverage_acceptance(self, selected, events):
        categories = {
            "accepted_with_evidence": [],
            "rejected_or_withdrawn": [],
            "approved_but_unaccepted": [],
        }
        exact = events.filtered(
            lambda row: row.document_revision_id == self
            and row.decision_source == "internal_proxy"
        ).sorted("id", reverse=True)
        by_requirement = {}
        for event in exact:
            by_requirement.setdefault(event.requirement_revision_id.id, event)
        for revision in selected:
            latest = by_requirement.get(revision.id)
            label = requirement_label(revision)
            if latest:
                latest._check_event_read()
                category = (
                    "accepted_with_evidence"
                    if latest.decision == "accepted"
                    else "rejected_or_withdrawn"
                )
                categories[category].append(
                    dict(
                        label,
                        decision=latest.decision,
                        asserted_authority=latest.authority_label,
                        authority_notice=_(
                            "Named authority is an internal assertion, "
                            "not external authentication or legal signature."
                        ),
                        authenticated_recorder=latest.recorded_by_label,
                        criteria=latest.criteria_evaluated,
                        evidence=latest.evidence,
                        recorded_at=fields.Datetime.to_string(latest.recorded_at),
                    )
                )
            elif self.state in ("approved", "superseded"):
                categories["approved_but_unaccepted"].append(label)
        return categories

    def _coverage_portal(self, events):
        exact = events.filtered(
            lambda row: row.document_revision_id == self
            and row.decision_source == "portal"
        ).sorted("id", reverse=True)
        latest = {}
        history = []
        for event in exact:
            event._check_event_read()
            receipt = dict(
                requirement_label(event.requirement_revision_id),
                **event._portal_receipt(),
            )
            history.append(receipt)
            latest.setdefault(event.requirement_revision_id.id, receipt)
        return {
            "authenticated_client_decisions": list(latest.values()),
            "authenticated_client_history": history,
        }

    def _coverage_changes(self, payload, baseline):
        if baseline is None:
            return {
                "status": "not_selected",
                "requirements": {},
                "contexts": {},
                "narrative_changed": None,
            }
        result: dict[str, object] = {"status": "compared"}
        for name in ("requirements", "contexts"):
            before = {row["key"]: row for row in baseline.get(name, [])}
            after = {row["key"]: row for row in payload.get(name, [])}
            result[name] = {
                "added": sorted(after.keys() - before.keys()),
                "removed": sorted(before.keys() - after.keys()),
                "changed": sorted(
                    key
                    for key in before.keys() & after.keys()
                    if before[key] != after[key]
                ),
            }

        def sections(rows):
            return [
                {key: value for key, value in row.items() if key != "section_id"}
                for row in rows
            ]

        result["narrative_changed"] = sections(payload["sections"]) != sections(
            baseline["sections"]
        )
        return result


# Preserve the established colocated exact-preview boundary; no structural move.
# pylint: disable-next=no-wizard-in-models
class SolutionPreviewWizard(models.TransientModel):
    _name = "project.agile.solution.preview.wizard"
    _description = "Explicit Exact Revision and Audience Preview"

    revision_id = fields.Many2one(
        "project.agile.solution.revision", required=True, ondelete="cascade"
    )
    document_id = fields.Many2one(related="revision_id.document_id")
    baseline_id = fields.Many2one("project.agile.solution.revision", ondelete="cascade")
    audience = fields.Selection(
        [("internal", "Internal"), ("customer", "Redacted Customer")],
        required=True,
        default="internal",
    )
    projection_text = fields.Text(compute="_compute_projection", compute_sudo=False)
    coverage_text = fields.Text(compute="_compute_projection", compute_sudo=False)
    native_revision_access = fields.Boolean(
        compute="_compute_revision_access", search="_search_revision_access"
    )

    def _compute_revision_access(self):
        for row in self:
            row.native_revision_access = True

    @api.model
    def default_get(self, names):
        protected = {
            "projection_text",
            "coverage_text",
            "native_revision_access",
            "document_id",
        }
        return {
            key: value
            for key, value in super()
            .default_get([name for name in names if name not in protected])
            .items()
            if key not in protected
        }

    def _search_revision_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        revisions = (
            self.env["project.agile.solution.revision"]
            .sudo(False)
            .with_context(active_test=False)
        )
        accessible = Domain.AND(
            [
                Domain("revision_id", "in", revisions._search([])),
                Domain.OR(
                    [
                        Domain("baseline_id", "=", False),
                        Domain("baseline_id", "in", revisions._search([])),
                    ]
                ),
            ]
        )
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    @api.model_create_multi
    def create(self, vals_list):
        caller = self.sudo(False)
        caller.check_access("create")
        prepared = [caller._prepare_preview(values) for values in vals_list]
        with self.env.cr.savepoint():
            rows = super(SolutionPreviewWizard, caller).create(prepared)
            rows._check_references()
            return rows

    def _prepare_preview(self, values):
        if set(values) - {"revision_id", "baseline_id", "audience"}:
            raise ValidationError(
                _("Preview output is a checked projection, not editable content.")
            )
        defaults = self.default_get(["revision_id", "baseline_id", "audience"])
        values = {**defaults, **values}
        revision = self.env["project.agile.solution.revision"]._checked_relation(
            "project.agile.solution.revision", values.get("revision_id")
        )
        revision._render_payload()
        if values.get("baseline_id"):
            revision._coverage_baseline(values["baseline_id"])
        return values

    def write(self, values):
        caller = self.sudo(False)
        caller.check_access("write")
        if set(values) - {"revision_id", "baseline_id", "audience"}:
            raise ValidationError(_("Preview output is not editable."))
        if "revision_id" in values:
            caller.env["project.agile.solution.revision"]._checked_relation(
                "project.agile.solution.revision", values["revision_id"]
            )
        if values.get("baseline_id"):
            caller.env["project.agile.solution.revision"]._checked_relation(
                "project.agile.solution.revision", values["baseline_id"]
            )
        with self.env.cr.savepoint():
            result = super(SolutionPreviewWizard, caller).write(values)
            caller._check_references()
            return result

    def _check_references(self):
        for row in self:
            if not row.revision_id and not row._origin:
                continue  # Native unsaved Form defaults have no selected revision.
            row.revision_id.sudo(False)._render_payload()
            if row.baseline_id:
                row.revision_id.sudo(False)._coverage_baseline(row.baseline_id.id)

    @api.depends("revision_id", "baseline_id", "audience")
    @api.depends_context("uid")
    def _compute_projection(self):
        for row in self:
            if not row.revision_id:
                row.projection_text = row.coverage_text = False
                continue
            revision = row.revision_id.sudo(False)
            row.projection_text = json.dumps(
                revision.action_projection(row.audience), ensure_ascii=False, indent=2
            )
            row.coverage_text = (
                json.dumps(
                    revision.action_coverage(row.baseline_id.id or None),
                    ensure_ascii=False,
                    indent=2,
                )
                if row.audience == "internal"
                else _("Coverage and acceptance evidence are internal only.")
            )

    def read(self, fields=None, load="_classic_read"):
        self._check_references()
        self.invalidate_recordset(["projection_text", "coverage_text"])
        return super().read(fields, load=load)

    def export_data(self, fields_to_export):
        self._check_references()
        self.invalidate_recordset(["projection_text", "coverage_text"])
        return super().export_data(fields_to_export)

    def action_render(self):
        self.ensure_one()
        self.sudo(False).check_access("read")
        self._check_references()
        name = (
            "report_solution_customer_action"
            if self.audience == "customer"
            else "report_solution_internal_action"
        )
        return self.env.ref("project_agile_solution." + name).report_action(
            self.revision_id.sudo(False)
        )

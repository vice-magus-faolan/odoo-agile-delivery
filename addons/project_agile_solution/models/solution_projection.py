"""Audience-safe native projections of exact structured content, never a master."""

import json
from html.parser import HTMLParser

from odoo import _, models
from odoo.exceptions import AccessError, ValidationError


class _NarrativeText(HTMLParser):
    """Discard markup/remote resources; never mark user text safe for QWeb."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3") and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def narrative_text(value):
    parser = _NarrativeText()
    parser.feed(value or "")
    return "".join(parser.parts).strip()


def audience_rows(rows, audience, excluded_kinds=()):
    """One finite filter shared by narrative, intent and typed context projections."""
    return [
        row
        for row in rows
        if audience == "internal"
        or row["audience"] == "customer"
        and row.get("kind") not in excluded_kinds
    ]


class SolutionProjection(models.Model):
    # Audience rendering is a separate boundary from coverage computation.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "project.agile.solution.revision"

    def _render_payload(self):
        """Revalidate closure on every call, including after a cached prior read."""
        self.ensure_one()
        caller = self.sudo(False).with_context(active_test=False)
        if not caller.env.user.active or not caller.env.user.has_group(
            "project.group_project_user"
        ):
            raise AccessError(_("An authorized internal Project user is required."))
        if caller.search_count([("id", "=", caller.id)]) != 1:
            raise AccessError(
                _("Exact solution content is unavailable under current access.")
            )
        caller.check_access("read")
        if caller.state == "draft":
            return caller._snapshot_payload()
        raw = caller.action_read_snapshot()["snapshot_json"]
        if not raw:
            raise AccessError(
                _("Exact solution content is unavailable under current access.")
            )
        payload = json.loads(raw)
        caller._check_snapshot_closure(payload)
        return payload

    def action_projection(self, audience="internal"):
        """Explicit exact revision and finite audience; customer is a redacted
        preview.
        """
        if type(audience) is not str or audience not in ("internal", "customer"):
            raise ValidationError(_("Select Internal or Customer projection."))
        payload = self._render_payload()
        sections = [
            self._project_section(row)
            for row in audience_rows(payload["sections"], audience)
        ]
        requirements = [
            self._project_requirement(row)
            for row in audience_rows(payload.get("requirements", []), audience)
        ]
        contexts = [
            self._project_context(row, audience)
            for row in audience_rows(
                payload.get("contexts", []), audience, ("question", "decision", "actor")
            )
        ]
        return {
            "title": payload["title"],
            "document_name": payload["document_name"],
            "project_name": payload["project_name"],
            "solution_name": payload["solution_name"],
            "number": payload["number"],
            "kind": payload["kind"],
            "audience": audience,
            "status": self.sudo(False).state,
            "notice": (
                _("Redacted customer projection; not the full internal baseline.")
                if audience == "customer"
                else _("Full internal projection; current reference closure checked.")
            ),
            "approval_notice": (
                _(
                    "Exact approved content; "
                    "supersession does not rewrite this baseline."
                )
                if self.state in ("approved", "superseded")
                else _(
                    "Unapproved working/review content; "
                    "not acceptance or scope approval."
                )
            ),
            "scope_disposition": payload["scope_disposition"],
            "scope_change_reason": payload["scope_change_reason"]
            if audience == "internal"
            else "",
            "approved_by": self.approved_by_label if audience == "internal" else "",
            "approved_at": str(self.approved_at) if self.approved_at else "",
            "sections": sections,
            "requirements": requirements,
            "contexts": contexts,
        }

    def _project_section(self, row):
        return {"title": row["title"], "text": narrative_text(row["body"])}

    def _project_requirement(self, row):
        names = (
            "key",
            "number",
            "title",
            "requirement_type",
            "description",
            "rationale",
            "priority",
            "verification_method",
            "acceptance_expectations",
        )
        return {name: row[name] for name in names}

    def _project_context(self, row, audience):
        result = {
            "title": row["title"],
            "kind": row["kind"],
            "text": narrative_text(row["body"]),
        }
        names = {
            "deliverable": ("evaluation_expectations",),
            "actor": ("business_role",),
            "question": (
                "question",
                "planning_significance",
                "resolution_status",
                "resolution",
                "resolution_rationale",
                "owner_label",
                "external_owner",
                "resolved_by_label",
                "resolved_at",
            ),
            "decision": ("decision_context", "choice", "consequences"),
        }.get(row["kind"], ())
        result["details"] = [
            {"label": name.replace("_", " ").title(), "text": row.get(name) or ""}
            for name in names
        ]
        # No raw reference IDs, owner IDs, external contacts, Task labels or
        # internal affected-requirement counts cross the customer boundary.
        result["requirements"] = [
            self._project_requirement(values)
            for values in row.get("affected_requirements", [])
            if audience == "internal" or values["audience"] == "customer"
        ]
        result["work"] = (
            [
                {"key": item["key"], "title": item["title"]}
                for item in row.get("spikes", [])
            ]
            if audience == "internal"
            else []
        )
        return result

    def action_preview_projection(self):
        self._render_payload()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.agile.solution.preview.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_revision_id": self.id},
        }


class InternalSolutionReport(models.AbstractModel):
    _name = "report.project_agile_solution.report_solution_internal"
    _description = "Exact Internal Solution Projection"
    _audience = "internal"

    def _get_report_values(self, docids, data=None):
        if (
            not isinstance(docids, (list, tuple))
            or len(docids) != 1
            or type(docids[0]) is not int
            or docids[0] <= 0
        ):
            raise ValidationError(_("Select one exact solution revision."))
        revision = (
            self.env["project.agile.solution.revision"].sudo(False).browse(docids)
        )
        # Report identity determines audience. Forged data/context cannot replace
        # the projection, docs, audience or revision, even on native direct routes.
        return {
            "projection": revision.action_projection(self._audience),
            "doc_ids": docids,
            "doc_model": revision._name,
            "docs": False,
        }


class CustomerSolutionReport(models.AbstractModel):
    _name = "report.project_agile_solution.report_solution_customer"
    _inherit = "report.project_agile_solution.report_solution_internal"
    _description = "Redacted Exact Customer Solution Projection"
    _audience = "customer"

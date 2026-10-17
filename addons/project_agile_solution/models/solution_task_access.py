"""Finite Task authority and exact traceability scope."""

from odoo import _, fields, models
from odoo.exceptions import AccessError, ValidationError


def check_task(task, project, mutation=True, active=True):
    """Resolve literal native Task authority, never caller context or sudo."""
    task = task.sudo(False).with_context(active_test=False)
    task.check_access("write" if mutation else "read")
    if len(task.exists()) != 1:
        raise ValidationError(_("Select one available native Task."))
    task.project_id.check_access("read")
    if task.project_id != project or task.company_id != project.company_id:
        raise ValidationError(_("Select work in this Project and company."))
    if active and (
        not task.active
        or not project.active
        or not project.agile_enabled
        or not task.agile_item_type_id
        or task.has_template_ancestor
        or task.has_project_template
    ):
        raise ValidationError(_("Select active, non-template native Agile work."))
    return task


def check_requirements(requirements, solution, active=True):
    requirements = requirements.sudo(False).with_context(active_test=False)
    requirements.check_access("read")
    requirements.requirement_id.check_access("read")
    if not requirements or len(requirements.exists()) != len(requirements):
        raise ValidationError(_("Select available exact requirements."))
    if any(row.solution_id != solution for row in requirements):
        raise ValidationError(_("Select exact revisions in this solution."))
    if active and (
        not solution.active
        or not solution.project_id.active
        or not solution.project_id.agile_enabled
        or any(not row.requirement_id.active for row in requirements)
    ):
        raise ValidationError(_("Select active solution requirements."))
    requirements._validate_content()
    return requirements


def check_document(document, requirements, solution):
    if not document:
        return
    document = document.sudo(False).with_context(active_test=False)
    document.check_access("read")
    if document.solution_id != solution or document.kind != "spec":
        raise ValidationError(_("Select an exact specification in this solution."))
    document._validate_content()
    if not requirements <= document.requirement_revision_ids:
        raise ValidationError(
            _("The specification must contain these exact requirement revisions.")
        )


class TaskTraceAccess(models.AbstractModel):
    _name = "project.agile.solution.task.access"
    _inherit = "project.agile.solution.access"
    _description = "Current Task and Exact Requirement Closure"

    task_id = fields.Many2one("project.task")
    document_revision_id = fields.Many2one("project.agile.solution.revision")

    def _search_native_project_access(self, operator, value):
        from odoo.fields import Domain

        if operator not in ("in", "not in"):
            return NotImplemented
        env = self.env
        solutions = (
            env["project.agile.solution"].sudo(False).with_context(active_test=False)
        )
        tasks = env["project.task"].sudo(False).with_context(active_test=False)
        documents = (
            env["project.agile.solution.revision"]
            .sudo(False)
            .with_context(active_test=False)
        )
        revisions = (
            env["project.agile.requirement.revision"]
            .sudo(False)
            .with_context(active_test=False)
        )
        clauses = [
            Domain("solution_id", "in", solutions._search([])),
            Domain.OR(
                [
                    Domain("task_id", "=", False),
                    Domain("task_id", "in", tasks._search([])),
                ]
            ),
            Domain.OR(
                [
                    Domain("document_revision_id", "=", False),
                    Domain("document_revision_id", "in", documents._search([])),
                ]
            ),
        ]
        if self._name == "project.agile.requirement.task.link":
            clauses.append(
                Domain("requirement_revision_id", "in", revisions._search([]))
            )
        else:
            # Explicit RHS subquery retains caller rules during sudo rule compilation.
            clauses.append(
                Domain(
                    "requirement_revision_ids",
                    "not any",
                    Domain("id", "not in", revisions._search([])),
                )
            )
        accessible = Domain.AND(clauses)
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    def _trace_authority(self):
        caller = self._check_authority()
        if caller.company_id and caller.company_id not in caller.env.user.company_ids:
            raise AccessError(_("Current company membership is required."))
        return caller

    def read(self, fields=None, load="_classic_read"):
        self._check_current_trace_read()
        return super().read(fields, load)

    def export_data(self, fields_to_export):
        self._check_current_trace_read()
        return super().export_data(fields_to_export)

    def _check_current_trace_read(self):
        # check_access may reuse an earlier recordset check. A fresh rule-bound
        # query closes cached/nonstored projections after reference rules change.
        # onchange pseudo-records have no stored row; check their persisted
        # origin when present, while allowing a fresh unsaved proposal.
        caller = self._origin.sudo(False).with_context(active_test=False)
        if caller.search_count([("id", "in", caller.ids)]) != len(caller):
            raise AccessError(
                _("Exact work context is unavailable under current access.")
            )

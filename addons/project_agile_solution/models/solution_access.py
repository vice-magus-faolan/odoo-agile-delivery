"""Shared current-caller authority and native Project authority."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from .project_agile_solution import ProjectAgileSolution


class SolutionAccess(models.AbstractModel):
    _name = "project.agile.solution.access"
    _description = "Current Native Solution Project Authority"

    solution_id = fields.Many2one("project.agile.solution")
    project_id = fields.Many2one(
        related="solution_id.project_id", store=True, index=True
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, index=True
    )
    native_project_access = fields.Boolean(
        compute="_compute_native_project_access",
        search="_search_native_project_access",
    )

    _compute_native_project_access = ProjectAgileSolution._compute_native_project_access

    @api.model
    def default_get(self, names):
        values = super().default_get(names)
        for name in ("project_id", "company_id", "native_project_access"):
            values.pop(name, None)
        if self._fields["solution_id"].related:
            values.pop("solution_id", None)
        return values

    def _search_native_project_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        parents = {
            "project.agile.solution.document": (
                "solution_id",
                "project.agile.solution",
            ),
            "project.agile.solution.revision": (
                "document_id",
                "project.agile.solution.document",
            ),
            "project.agile.solution.section": (
                "revision_id",
                "project.agile.solution.revision",
            ),
            "project.agile.requirement": ("solution_id", "project.agile.solution"),
            "project.agile.requirement.revision": (
                "requirement_id",
                "project.agile.requirement",
            ),
            "project.agile.solution.context": ("solution_id", "project.agile.solution"),
            "project.agile.solution.context.revision": (
                "context_id",
                "project.agile.solution.context",
            ),
        }
        field, model = parents[self._name]
        parent = self.env[model].sudo(False).with_context(active_test=False)
        projects = (
            self.env["project.project"].sudo(False).with_context(active_test=False)
        )
        accessible = Domain.AND(
            [
                Domain("project_id", "in", projects._search([])),
                Domain(field, "in", parent._search([])),
            ]
        )
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    def _check_authority(self, operation="write"):
        """Ordinary sudo/context cannot select authority or bypass Project rules."""
        caller = self.sudo(False)
        caller.check_access(operation)
        if not caller.env.user.active or not caller.env.user.has_group(
            "project.group_project_manager"
        ):
            raise AccessError(
                _("An active Project Manager with current Project access is required.")
            )
        caller.project_id.check_access("read")
        caller.project_id.check_access("write")
        return caller

    def _checked_relation(self, model, record_id):
        if type(record_id) is not int or record_id <= 0:
            raise ValidationError(_("Select an available record in this solution."))
        record = (
            self.env[model]
            .sudo(False)
            .with_context(active_test=False)
            .browse(record_id)
            .exists()
        )
        record.check_access("read")
        if not record:
            raise ValidationError(_("Select an available record in this solution."))
        return record

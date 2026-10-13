"""Stable SOW/spec identity with independent designated approval chains."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .solution_access import lock_records


class SolutionDocument(models.Model):
    _name = "project.agile.solution.document"
    _inherit = "project.agile.solution.access"
    _description = "Solution Document Identity"
    _check_company_auto = True
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    solution_id = fields.Many2one(
        "project.agile.solution",
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
    )
    kind = fields.Selection(
        [
            ("sow", "Statement of Work"),
            ("spec", "Solution Specification / Internal Brief"),
        ],
        required=True,
        default="spec",
    )
    approver_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        default=lambda self: self.env.user,
    )
    revision_ids = fields.One2many(
        "project.agile.solution.revision", "document_id", readonly=True, copy=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        self.sudo(False).check_access("create")
        prepared = []
        for values in vals_list:
            values = dict(values)
            if {"project_id", "company_id", "revision_ids"} & values.keys():
                raise ValidationError(
                    _("Document scope and revisions are server managed.")
                )
            solution = self._checked_relation(
                "project.agile.solution", values.get("solution_id")
            )
            lock_records(solution, serialize=True)
            lock_records(solution.project_id)
            solution.sudo(False).check_access("write")
            solution.project_id.sudo(False).check_access("write")
            if (
                not solution.active
                or not solution.project_id.active
                or not solution.project_id.agile_enabled
            ):
                raise ValidationError(_("Select an active Agile solution."))
            prepared.append(values)
        with self.env.cr.savepoint():
            records = super().create(prepared)
            records._check_authority()
        return records

    @api.constrains("approver_id", "company_id")
    def _check_approver(self):
        for record in self:
            approver = record.approver_id
            if (
                not approver.active
                or approver.share
                or not approver.has_group("project.group_project_manager")
            ):
                raise ValidationError(
                    _("Designate an active internal Project Manager approver.")
                )
            if record.company_id and record.company_id not in approver.company_ids:
                raise ValidationError(
                    _("The designated approver must belong to the Project company.")
                )

    def write(self, values):
        self._check_authority()
        self._lock_scope()
        if {
            "solution_id",
            "project_id",
            "company_id",
            "kind",
            "revision_ids",
        } & values.keys():
            raise ValidationError(
                _(
                    "Document identity/scope/kind cannot be reassigned. "
                    "Edit a draft revision instead."
                )
            )
        with self.env.cr.savepoint():
            return super().write(values)

    def unlink(self):
        self._check_authority("unlink")
        self._lock_scope()
        if self.with_context(active_test=False).revision_ids:
            # Retention rejects deleting a document with historical revisions.
            raise ValidationError(  # pylint: disable=no-raise-unlink
                _(
                    "Remove only unused draft revisions explicitly; "
                    "retain reviewed document history."
                )
            )
        return super().unlink()

    def action_new_revision(self):
        self.ensure_one()
        self._check_authority()
        self._lock_scope()
        revisions = self._complete_revisions()
        if revisions:
            if revisions[-1].state in ("draft", "review"):
                return revisions[-1]._form_action()
            return revisions[-1].action_new_revision()
        revision = self.env["project.agile.solution.revision"].create(
            {"document_id": self.id, "title": self.name}
        )
        return revision._form_action()

    def _complete_revisions(self):
        self.ensure_one()
        revisions = self.with_context(active_test=False).revision_ids
        total = (
            self.env["project.agile.solution.revision"]
            .sudo()
            .with_context(active_test=False)
            .search_count([("document_id", "=", self.id)])
        )
        if total != len(revisions):
            raise AccessError(
                _("Document history is unavailable under current access.")
            )
        return revisions.sorted("number")

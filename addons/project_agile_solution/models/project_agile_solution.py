"""Project-scoped solution lineage, not a Task or an approved specification."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ProjectAgileSolution(models.Model):
    """Keep solution identity separate from later immutable document revisions."""

    _name = "project.agile.solution"
    _description = "Agile Solution Lineage"
    _check_company_auto = True
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    project_id = fields.Many2one(
        "project.project",
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
        copy=False,
    )
    company_id = fields.Many2one(
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    native_project_access = fields.Boolean(
        compute="_compute_native_project_access",
        search="_search_native_project_access",
    )

    _last_document_id = fields.Many2one(
        "project.agile.solution.document",
        readonly=True,
        copy=False,
        ondelete="set null",
        groups="project_agile_solution.group_snapshot_storage",
        help=(
            "Published by document creation to conflict with concurrent scope "
            "approval and lineage removal."
        ),
    )
    _last_approved_revision_id = fields.Many2one(
        "project.agile.solution.revision",
        readonly=True,
        copy=False,
        ondelete="set null",
        groups="project_agile_solution.group_snapshot_storage",
        help=(
            "Published by document approval to order concurrent SOW and "
            "specification approvals."
        ),
    )

    @api.model
    def default_get(self, names):
        return super().default_get(
            [
                name
                for name in names
                if name
                not in {
                    "_last_document_id",
                    "_last_approved_revision_id",
                }
            ]
        )

    def _record_document(self, document):
        self.ensure_one()
        if document.solution_id != self:
            raise ValidationError(_("Document history must retain its solution."))
        return super(ProjectAgileSolution, self.sudo()).write(
            {"_last_document_id": document.id}
        )

    def _record_approval(self, revision):
        self.ensure_one()
        if revision.solution_id != self:
            raise ValidationError(_("Approval must retain its solution."))
        return super(ProjectAgileSolution, self.sudo()).write(
            {"_last_approved_revision_id": revision.id}
        )

    def _compute_native_project_access(self):
        """Accessible lineage records have passed the global Project-access rule."""
        for record in self:
            record.native_project_access = True

    def _search_native_project_access(self, operator, value):
        """Compile a current-user subquery even when rule compilation uses sudo.

        Odoo 19 BaseModel._search optimizes rule domains on a sudo recordset;
        a plain relational ``any`` therefore does not retain Project rules.
        Keep the query unevaluated to avoid caching/materializing Project IDs.
        This private native API is pinned and covered by real rule-change tests.
        """
        if operator not in ("in", "not in"):
            return NotImplemented
        projects = (
            self.env["project.project"].sudo(False).with_context(active_test=False)
        )
        accessible = Domain("project_id", "in", projects._search([]))
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    @api.model_create_multi
    def create(self, vals_list):
        """Resolve native Project authority before storing any lineage."""
        self.check_access("create")
        defaults = self.default_get(["project_id"])
        prepared = []
        for values in vals_list:
            values = dict(values)
            if {"_last_document_id", "_last_approved_revision_id"} & values.keys():
                raise ValidationError(_("History publication is server managed."))
            if "company_id" in values:
                raise ValidationError(
                    _("Solution company is determined by its Project.")
                )
            project_id = values.get("project_id", defaults.get("project_id"))
            project = self._validated_project(project_id)
            values["project_id"] = project.id
            prepared.append(values)
        return super().create(prepared)

    def _validated_project(self, project_id):
        """No context flag, related-field computation or elevation grants access."""
        if type(project_id) is not int or project_id <= 0:
            raise ValidationError(_("Select an available Agile Project."))
        project = self.env["project.project"].browse(project_id).exists()
        project.check_access("read")
        project.check_access("write")
        if not project or not project.active or not project.agile_enabled:
            raise ValidationError(_("Select an active Agile Project."))
        return project

    def write(self, values):
        """Archive/rename identity; never move it between Projects or companies."""
        self.check_access("write")
        if {
            "project_id",
            "company_id",
            "_last_document_id",
            "_last_approved_revision_id",
        } & values.keys():
            raise ValidationError(
                _("A solution lineage cannot change Project or company.")
            )
        self.project_id.check_access("write")
        return super().write(values)

    def unlink(self):
        """Only unused root identities are deletable; later history restricts
        deletion.
        """
        self.check_access("unlink")
        self.project_id.check_access("write")
        return super().unlink()

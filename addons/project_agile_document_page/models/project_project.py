from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProjectProject(models.Model):
    _inherit = "project.project"

    agile_documentation_page_id = fields.Many2one(
        "document.page",
        string="Agile Documentation Root",
        copy=False,
        ondelete="set null",
    )

    def _check_agile_documentation_project_access(self, operation):
        self.ensure_one()
        self.check_access(operation)

    def _check_agile_documentation_page_read_access(self, page):
        page.check_access("read")

    def _validate_agile_documentation_root(self, error_class=ValidationError):
        self.ensure_one()
        page = self.agile_documentation_page_id
        if not page:
            return
        self._check_agile_documentation_page_read_access(page)
        if not self.agile_enabled:
            raise error_class(_("Only Agile projects can have a documentation root."))
        if page.type != "content" or not page.active:
            raise error_class(_("The Agile documentation root must be an active content page."))
        if page.project_id != self:
            raise error_class(_("The documentation root must belong to this project."))
        if page.company_id and page.company_id != self.company_id:
            raise error_class(_("The documentation root must belong to the project company."))

    @api.constrains("agile_enabled", "agile_documentation_page_id", "company_id")
    def _check_agile_documentation_root(self):
        for project in self:
            project._validate_agile_documentation_root()

    def _check_agile_documentation_write_access(self):
        self._check_agile_documentation_project_access("write")
        if not self.agile_enabled:
            raise UserError(_("Enable Agile before managing a documentation root."))

    def _documentation_page_action(self, page):
        self._check_agile_documentation_project_access("read")
        self._check_agile_documentation_page_read_access(page)
        if not page.active:
            raise UserError(_("The Agile documentation root is archived."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "document.page",
            "res_id": page.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_agile_documentation_root(self):
        self._check_agile_documentation_write_access()
        if self.agile_documentation_page_id:
            raise UserError(_("Clear the current Agile documentation root before creating another one."))
        page_model = self.env["document.page"]
        page_model.check_access("create")
        page = page_model.create(
            {
                "name": _("%(project)s Documentation", project=self.name),
                "type": "content",
                "project_id": self.id,
                "company_id": self.company_id.id,
            }
        )
        self.agile_documentation_page_id = page
        return self._documentation_page_action(page)

    def action_open_agile_documentation_root(self):
        self.ensure_one()
        page = self.agile_documentation_page_id
        if not page:
            raise UserError(_("Set an Agile documentation root before opening it."))
        self._validate_agile_documentation_root(UserError)
        return self._documentation_page_action(page)

    def action_clear_agile_documentation_root(self):
        self._check_agile_documentation_write_access()
        self.agile_documentation_page_id = False
        return True

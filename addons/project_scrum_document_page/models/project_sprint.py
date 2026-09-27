from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProjectSprint(models.Model):
    _inherit = "project.sprint"

    retrospective_page_id = fields.Many2one(
        "document.page",
        string="Retrospective",
        copy=False,
        ondelete="set null",
    )

    def _check_retrospective_write_access(self):
        self.ensure_one()
        self.check_access("write")
        if self.state == "closed":
            raise UserError(_("Closed Sprints cannot change their retrospective link."))

    def write(self, values):
        if "retrospective_page_id" in values and any(sprint.state == "closed" for sprint in self):
            raise UserError(_("Closed Sprints cannot change their retrospective link."))
        return super().write(values)

    def _validate_retrospective_page(self, error_class=ValidationError):
        self.ensure_one()
        page = self.retrospective_page_id
        if not page:
            return
        page.check_access("read")
        if page.type != "content" or not page.active:
            raise error_class(_("The retrospective must be an active content page."))
        if page.project_id != self.project_id:
            raise error_class(_("The retrospective must belong to the Sprint project."))
        if page.company_id != self.company_id:
            raise error_class(_("The retrospective must belong to the Sprint company."))

    @api.constrains("retrospective_page_id", "project_id", "company_id")
    def _check_retrospective_page(self):
        for sprint in self:
            sprint._validate_retrospective_page()

    def _retrospective_page_action(self, page):
        self.ensure_one()
        self.check_access("read")
        self._validate_retrospective_page(UserError)
        return {
            "type": "ir.actions.act_window",
            "res_model": "document.page",
            "res_id": page.id,
            "view_mode": "form",
            "target": "current",
        }

    def _retrospective_template(self):
        template = self.env.ref(
            "project_scrum_document_page.document_page_category_sprint_retrospective",
            raise_if_not_found=False,
        )
        if not template or not template.exists() or not template.active or template.type != "category":
            raise UserError(_("The Sprint Retrospective template is unavailable."))
        template.check_access("read")
        return template

    def action_create_retrospective_page(self):
        self.ensure_one()
        self._check_retrospective_write_access()
        if self.retrospective_page_id:
            return self._retrospective_page_action(self.retrospective_page_id)
        template = self._retrospective_template()
        page_model = self.env["document.page"]
        page_model.check_access("create")
        page = page_model.create(
            {
                "name": _("%(sprint)s Retrospective", sprint=self.name),
                "type": "content",
                "parent_id": template.id,
                "content": template.template,
                "project_id": self.project_id.id,
                "company_id": self.company_id.id,
            }
        )
        self.retrospective_page_id = page
        return self._retrospective_page_action(page)

    def action_open_retrospective_page(self):
        self.ensure_one()
        if not self.retrospective_page_id:
            raise UserError(_("Set a retrospective before opening it."))
        return self._retrospective_page_action(self.retrospective_page_id)

    def action_clear_retrospective_page(self):
        self._check_retrospective_write_access()
        self.retrospective_page_id = False
        return True

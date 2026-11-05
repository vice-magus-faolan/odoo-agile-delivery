from odoo import fields, models


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = "project.template.create.wizard"

    agile_enabled = fields.Boolean(related="template_id.agile_enabled")
    agile_key = fields.Char()

    def _get_template_whitelist_fields(self):
        names = super()._get_template_whitelist_fields()
        # Do not inject Agile configuration into ordinary template creation.
        if self.template_id.agile_enabled:
            names = [*names, "agile_key"]
        return names

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectAgileTeam(models.Model):
    """A named delivery team for one opt-in Agile project."""

    _name = "project.agile.team"
    _description = "Agile Delivery Team"
    _order = "project_id, name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    project_id = fields.Many2one("project.project", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="project_id.company_id", store=True, readonly=True, index=True)

    @api.constrains("project_id")
    def _check_agile_project(self):
        for team in self:
            if team.project_id and not team.project_id.agile_enabled:
                raise ValidationError(_("Agile teams require an Agile-enabled project."))

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


def check_scrum_project(project):
    # Scrum ACLs never substitute for current native Project authority.
    project = project._check_agile_project_access()
    if any(not row.active or not row.agile_enabled for row in project):
        raise ValidationError(project.env._("Select an active Agile Project."))


class ProjectAgileTeam(models.Model):
    """A named delivery team for one opt-in Agile project."""

    _name = "project.agile.team"
    _description = "Agile Delivery Team"
    _order = "project_id, name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    project_id = fields.Many2one(
        "project.project", required=True, ondelete="restrict", index=True
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, index=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        with self.env.cr.savepoint():
            teams = super().create(vals_list)
            check_scrum_project(teams.project_id)
            return teams

    def write(self, values):
        self.sudo(False).check_access("write")
        check_scrum_project(self.project_id)
        with self.env.cr.savepoint():
            result = super().write(values)
            check_scrum_project(self.project_id)
            return result

    @api.constrains("project_id")
    def _check_agile_project(self):
        for team in self:
            if team.project_id and not team.project_id.agile_enabled:
                raise ValidationError(
                    _("Agile teams require an Agile-enabled project.")
                )

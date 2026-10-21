from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.project_agile.utils import claim_records


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
    membership_revision = fields.Integer(
        default=0,
        readonly=True,
        copy=False,
        groups="base.group_system",
        help=(
            "Advanced by Task and Sprint placement changes so they conflict "
            "with concurrent team or Sprint ownership edits."
        ),
    )

    def _register_membership(self):
        """Invalidate old ownership snapshots at the shared team boundary."""
        if not self:
            return
        self.check_access("read")
        self.project_id.check_access("read")
        claim_records(self, allow_referencing=True)
        # The caller may place editable Tasks without team configuration authority.
        # Only this private revision write is elevated, not the placement itself.
        for team in self.sudo():
            super(ProjectAgileTeam, team).write(
                {"membership_revision": team.membership_revision + 1}
            )
        self.sudo().flush_recordset(["membership_revision"])

    @api.model_create_multi
    def create(self, vals_list):
        with self.env.cr.savepoint():
            teams = super().create(vals_list)
            check_scrum_project(teams.project_id)
            return teams

    def write(self, values):
        self.sudo(False).check_access("write")
        check_scrum_project(self.project_id)
        if "project_id" in values:
            changing = self.filtered(
                lambda team: team.project_id.id != values["project_id"]
            )
            claim_records(changing, allow_referencing=True)
            # Search as superuser so hidden and archived tasks still block the change.
            if changing and (
                self.env["project.sprint"]
                .sudo()
                .search_count([("team_id", "in", changing.ids)], limit=1)
                or self.env["project.task"]
                .sudo()
                .with_context(active_test=False)
                .search_count([("agile_team_id", "in", changing.ids)], limit=1)
            ):
                raise ValidationError(
                    self.env._("A team used by tasks or Sprints cannot change Project.")
                )
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

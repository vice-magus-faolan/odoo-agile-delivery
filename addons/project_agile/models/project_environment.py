from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain


class ProjectAgileEnvironment(models.Model):
    _name = "project.agile.environment"
    _description = "Client Project Environment"
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_production = fields.Boolean(string="Production")
    project_id = fields.Many2one(
        "project.project",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(related="project_id.company_id", store=True)
    native_access = fields.Boolean(
        compute="_compute_native_access", search="_search_native_access"
    )

    def _compute_native_access(self):
        for environment in self:
            environment.native_access = environment.project_id.sudo(False).has_access(
                "read"
            )

    def _search_native_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        projects = (
            self.env["project.project"].sudo(False).with_context(active_test=False)
        )
        accessible = Domain("project_id", "in", projects._search([]))
        positive = Domain.OR(accessible if flag else ~accessible for flag in value)
        return positive if operator == "in" else ~positive

    def _check_configuration_access(self):
        if not self.env.su and not self.env.user.has_group(
            "project.group_project_manager"
        ):
            raise AccessError(
                self.env._("Only a Project administrator may configure environments.")
            )
        self.project_id.check_access("write")

    @api.constrains("project_id")
    def _check_agile_project(self):
        for environment in self:
            if not environment.project_id.agile_enabled:
                raise ValidationError(
                    self.env._("Environments require an Agile Project.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        projects = self.env["project.project"].browse(
            [
                values.get("project_id", self.env.context.get("default_project_id"))
                for values in vals_list
            ]
        )
        self._check_configuration_access()
        projects.check_access("write")
        environments = super().create(vals_list)
        environments.project_id._sync_open_environment_tasks()
        return environments

    def write(self, values):
        self._check_configuration_access()
        if "project_id" in values and any(
            environment.project_id.id != values["project_id"] for environment in self
        ):
            raise ValidationError(
                self.env._("An environment cannot move to another Project.")
            )
        result = super().write(values)
        if values.get("active"):
            self.project_id._sync_open_environment_tasks()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_recorded_history(self):
        self._check_configuration_access()
        if (
            self.env["project.task.environment.status"]
            .sudo()
            .search_count([("environment_id", "in", self.ids)], limit=1)
        ):
            raise ValidationError(
                self.env._(
                    "Archive environments with recorded task statuses "
                    "instead of deleting them."
                )
            )

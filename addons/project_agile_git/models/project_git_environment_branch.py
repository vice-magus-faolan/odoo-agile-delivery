"""Repository-specific environment branch configuration, never task status."""

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain


class ProjectGitEnvironmentBranch(models.Model):
    _name = "project.git.environment.branch"
    _description = "Environment Git Branch Mapping"
    _rec_name = "branch_name"
    _order = "project_id, environment_id, repository_id, id"
    _check_company_auto = True

    environment_id = fields.Many2one(
        "project.agile.environment",
        required=True,
        ondelete="cascade",
        check_company=True,
        index=True,
    )
    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        ondelete="cascade",
        check_company=True,
        index=True,
    )
    project_id = fields.Many2one(related="environment_id.project_id", store=True)
    company_id = fields.Many2one(related="environment_id.company_id", store=True)
    branch_name = fields.Char(string="Target branch", required=True)
    active = fields.Boolean(default=True)
    native_access = fields.Boolean(
        compute="_compute_native_access", search="_search_native_access"
    )

    _environment_repository_unique = models.Constraint(
        "UNIQUE(environment_id, repository_id)",
        "An environment can map a repository only once; edit or restore its mapping.",
    )

    def _compute_native_access(self):
        visible = self.search([("id", "in", self.ids)])
        for mapping in self:
            mapping.native_access = mapping in visible

    def _search_native_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        environments = self.env["project.agile.environment"].sudo(False)
        repositories = self.env["project.git.repository"].sudo(False)
        accessible = Domain(
            "environment_id",
            "in",
            environments.with_context(active_test=False)._search([]),
        ) & Domain(
            "repository_id",
            "in",
            repositories.with_context(active_test=False)._search([]),
        )
        positive = Domain.OR(accessible if flag else ~accessible for flag in value)
        return positive if operator == "in" else ~positive

    @api.model
    def _check_derived_input(self, values):
        defaults = {
            key.removeprefix("default_")
            for key in self.env.context
            if key.startswith("default_")
        }
        if {"project_id", "company_id", "native_access"}.intersection(
            values.keys() | defaults
        ):
            raise AccessError(
                self.env._("Mapping ownership is derived from its environment.")
            )

    def _check_configuration_access(self):
        self.env["project.agile.environment"]._check_configuration_access()
        self.environment_id.check_access("read")
        self.environment_id._check_configuration_access()
        self.repository_id.check_access("read")

    @api.constrains("environment_id", "repository_id", "branch_name")
    def _check_mapping(self):
        for mapping in self:
            if (
                mapping.environment_id.project_id != mapping.repository_id.project_id
                or mapping.environment_id.company_id != mapping.repository_id.company_id
                or not mapping.project_id.agile_enabled
            ):
                raise ValidationError(
                    self.env._(
                        "Map an environment and repository from the same "
                        "Agile Project and company."
                    )
                )
            branch = mapping.branch_name
            if branch.startswith("refs/heads/") or any(
                char.isspace() for char in branch
            ):
                raise ValidationError(
                    self.env._(
                        "Use an exact short Git branch name, such as release/uat, "
                        "without refs/heads/."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_configuration_access()
        defaults = self.default_get(["environment_id", "repository_id"])
        for values in vals_list:
            self._check_derived_input(values)
        environments = self.env["project.agile.environment"].browse(
            [
                values.get("environment_id", defaults.get("environment_id"))
                for values in vals_list
            ]
        )
        environments.check_access("read")
        environments._check_configuration_access()
        self.env["project.git.repository"].browse(
            [
                values.get("repository_id", defaults.get("repository_id"))
                for values in vals_list
            ]
        ).check_access("read")
        return super().create(vals_list)

    def write(self, values):
        self._check_derived_input(values)
        self._check_configuration_access()
        if values.get("environment_id"):
            environment = self.env["project.agile.environment"].browse(
                values["environment_id"]
            )
            environment.check_access("read")
            environment._check_configuration_access()
        if values.get("repository_id"):
            self.env["project.git.repository"].browse(
                values["repository_id"]
            ).check_access("read")
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_configuration_access(self):
        self._check_configuration_access()


class ProjectProject(models.Model):
    _inherit = "project.project"

    git_environment_branch_ids = fields.One2many(
        "project.git.environment.branch",
        "project_id",
        copy=False,
        string="Environment Git branches",
    )


class ProjectGitRepository(models.Model):
    _inherit = "project.git.repository"

    def write(self, values):
        if "project_id" in values and any(
            repo.project_id.id != values["project_id"] for repo in self
        ):
            # Integrity only: hidden mappings must prevent a repository move.
            # No elevated data enters the evidence projection.
            if (
                self.env["project.git.environment.branch"]
                .sudo()
                .with_context(
                    active_test=False,
                )
                .search_count([("repository_id", "in", self.ids)], limit=1)
            ):
                raise ValidationError(
                    self.env._(
                        "Remove environment branch mappings before moving a "
                        "repository to another Project."
                    )
                )
        return super().write(values)

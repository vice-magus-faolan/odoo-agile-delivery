"""Project-owned advisory limits; Task transitions remain entirely native."""

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain


class ProjectProject(models.Model):
    # Keep presentation policy out of the planning mutation service.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "project.project"

    agile_wip_enabled = fields.Boolean(
        string="Advisory WIP Limits",
        copy=False,
        help=(
            "Show caller-visible open work against stage limits on the Active "
            "Sprint board. Never blocks Task changes."
        ),
    )
    agile_wip_limit_ids = fields.One2many(
        "project.agile.wip.limit",
        "project_id",
        string="Stage WIP Limits",
        copy=False,
    )

    def _check_agile_configuration(self, values):
        if (
            {"agile_wip_enabled", "agile_wip_limit_ids"} & values.keys()
            and not self.env.su
            and not self.env.user.has_group("project.group_project_manager")
        ):
            raise AccessError(
                self.env._("Only a Project administrator may configure WIP limits.")
            )
        return super()._check_agile_configuration(values)

    def _agile_wip_summary(self, domain):
        """Aggregate the complete visible open scope, not the current card page."""
        self.ensure_one()
        if not self.agile_wip_enabled:
            return []
        policies = self.env["project.agile.wip.limit"].search(
            [("project_id", "=", self.id)]
        )
        stages = self.env["project.task.type"].search_fetch(
            [("id", "in", policies.stage_id.ids), ("project_ids", "in", self.ids)],
            ["name"],
            order="sequence, id",
        )
        limits = {policy.stage_id.id: policy.limit for policy in policies}
        rows = self.env["project.task"]._read_group(
            Domain(domain)
            & Domain("state", "not in", ["1_done", "1_canceled"])
            & Domain("stage_id", "in", stages.ids),
            ["stage_id"],
            ["__count"],
        )
        counts = {stage.id: count for stage, count in rows}
        return [
            {
                "id": stage.id,
                "name": stage.name,
                "limit": limits[stage.id],
                "count": counts.get(stage.id, 0),
                "overflow": max(0, counts.get(stage.id, 0) - limits[stage.id]),
            }
            for stage in stages
        ]


class ProjectAgileWipLimit(models.Model):
    _name = "project.agile.wip.limit"
    _description = "Project Advisory Stage WIP Limit"
    _rec_name = "stage_id"
    _check_company_auto = True

    project_id = fields.Many2one(
        "project.project",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(related="project_id.company_id", store=True)
    stage_id = fields.Many2one("project.task.type", required=True, ondelete="cascade")
    limit = fields.Integer(required=True, default=1, string="Advisory Limit")
    native_access = fields.Boolean(
        compute="_compute_native_access", search="_search_native_access"
    )

    _stage_unique = models.Constraint(
        "UNIQUE(project_id, stage_id)", "Configure each stage only once per Project."
    )
    _positive_limit = models.Constraint(
        'CHECK("limit" > 0)', "An advisory WIP limit must be positive."
    )

    def _compute_native_access(self):
        for policy in self:
            policy.native_access = policy.project_id.sudo(False).has_access(
                "read"
            ) and policy.stage_id.sudo(False).has_access("read")

    def _search_native_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        projects = (
            self.env["project.project"].sudo(False).with_context(active_test=False)
        )
        accessible = Domain("project_id", "in", projects._search([]))
        stages = self.env["project.task.type"].sudo(False)
        accessible &= Domain("stage_id", "in", stages._search([]))
        positive = Domain.OR(accessible if flag else ~accessible for flag in value)
        return positive if operator == "in" else ~positive

    def _check_configuration_access(self):
        if not self.env.su and not self.env.user.has_group(
            "project.group_project_manager"
        ):
            raise AccessError(
                self.env._("Only a Project administrator may configure WIP limits.")
            )
        self.project_id.check_access("write")

    @api.constrains("project_id", "stage_id")
    def _check_project_stage(self):
        for policy in self:
            if (
                not policy.project_id.agile_enabled
                or policy.project_id not in policy.stage_id.project_ids
            ):
                raise ValidationError(
                    self.env._("Choose a stage belonging to this Agile Project.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_configuration_access()
        projects = self.env["project.project"].browse(
            [
                values.get("project_id", self.env.context.get("default_project_id"))
                for values in vals_list
            ]
        )
        projects.check_access("write")
        return super().create(vals_list)

    def write(self, values):
        self._check_configuration_access()
        if "project_id" in values and any(
            policy.project_id.id != values["project_id"] for policy in self
        ):
            raise ValidationError(
                self.env._("A WIP limit cannot move to another Project.")
            )
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_configuration(self):
        self._check_configuration_access()

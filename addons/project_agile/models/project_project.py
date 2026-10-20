import re

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

_AGILE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*$")


class ProjectProject(models.Model):
    _inherit = "project.project"

    # Keep the explicit source labels/translation keys unchanged during adoption.
    # pylint: disable-next=attribute-string-redundant
    agile_enabled = fields.Boolean(string="Agile Enabled", copy=False)
    # pylint: disable-next=attribute-string-redundant
    agile_key = fields.Char(string="Agile Key", copy=False, index=True)
    agile_default_item_type_id = fields.Many2one(
        "project.agile.item.type", string="Default Agile Item Type", ondelete="restrict"
    )
    agile_estimation_method = fields.Selection(
        [("none", "None"), ("fibonacci", "Fibonacci")],
        default="none",
        string="Estimation Method",
    )

    _agile_key_unique = models.Constraint(
        "UNIQUE(agile_key)",
        "The Agile key must be unique across projects.",
    )

    @api.constrains("agile_enabled", "agile_key")
    def _check_agile_key(self):
        for project in self:
            if project.agile_enabled and not project.agile_key:
                raise ValidationError(_("An Agile project requires an Agile key."))
            if project.agile_key and not _AGILE_KEY_PATTERN.fullmatch(
                project.agile_key
            ):
                raise ValidationError(
                    _(
                        "The Agile key must start with an uppercase letter and "
                        "contain only uppercase letters and digits."
                    )
                )

    def _agile_sequence_code(self):
        self.ensure_one()
        return f"project_agile.task.{self.id}"

    def _ensure_agile_sequence(self):
        sequence_model = self.env["ir.sequence"].sudo()
        for project in self.filtered("agile_enabled"):
            code = project._agile_sequence_code()
            sequence = sequence_model.search([("code", "=", code)], limit=1)
            prefix = f"{project.agile_key}-"
            if sequence:
                sequence.write({"prefix": prefix})
                continue
            sequence_model.create(
                {
                    "name": _("Agile Task %(project)s", project=project.display_name),
                    "code": code,
                    "company_id": project.company_id.id or False,
                    "prefix": prefix,
                    "padding": 0,
                    "number_next": 1,
                    "number_increment": 1,
                    "implementation": "standard",
                }
            )

    def _next_agile_task_key(self):
        self.ensure_one()
        self._ensure_agile_sequence()
        sequence = (
            self.env["ir.sequence"]
            .sudo()
            .search([("code", "=", self._agile_sequence_code())], limit=1)
        )
        return sequence.next_by_id()

    def _check_agile_project_access(self):
        # Child author/operator ACLs do not grant native Project configuration.
        # Preserve the existing administrator write check; other roles need
        # current native visibility, including custom rules and company scope.
        if self.env.su and self.env.uid == SUPERUSER_ID:
            return self
        caller = self.sudo(False)
        if not caller.env.user.active:
            raise AccessError(_("An active internal Agile user is required."))
        caller.check_access("read")
        if caller.env.user.has_group("project.group_project_manager"):
            caller.check_access("write")
        return caller

    def _check_agile_configuration(self, values):
        protected = {
            "agile_enabled",
            "agile_key",
            "agile_default_item_type_id",
            "agile_estimation_method",
        }
        if self.env.su:
            return
        if protected & values.keys() and not self.sudo(False).env.user.has_group(
            "project.group_project_manager"
        ):
            raise AccessError(_("Only a Project administrator may configure Agile."))

    @api.model_create_multi
    def create(self, vals_list):
        defaults = {
            name.removeprefix("default_"): value
            for name, value in self.env.context.items()
            if name.startswith("default_agile_")
        }
        for values in vals_list:
            self._check_agile_configuration(defaults | values)
        vals_list = [dict(values) for values in vals_list]
        for values in vals_list:
            if (
                values.get("agile_enabled", defaults.get("agile_enabled"))
                and "agile_default_item_type_id" not in values
                and "agile_default_item_type_id" not in defaults
            ):
                item_type = self.env.ref(
                    "project_agile.project_agile_item_type_task",
                    raise_if_not_found=False,
                )
                if item_type and item_type.active:
                    values["agile_default_item_type_id"] = item_type.id
        projects = super().create(vals_list)
        projects._ensure_agile_sequence()
        return projects

    def write(self, values):
        self._check_agile_configuration(values)
        if "agile_key" in values:
            task_model = self.env["project.task"]
            for project in self:
                if values["agile_key"] != project.agile_key and task_model.search_count(
                    [("project_id", "=", project.id), ("agile_key", "!=", False)]
                ):
                    raise ValidationError(
                        _(
                            "The Agile key cannot change after task keys "
                            "have been assigned."
                        )
                    )
        projects_to_default = self.browse()
        if values.get("agile_enabled") and "agile_default_item_type_id" not in values:
            projects_to_default = self.filtered(
                lambda project: not project.agile_enabled
                and not project.agile_default_item_type_id
            )
        result = super().write(values)
        if projects_to_default:
            item_type = self.env.ref(
                "project_agile.project_agile_item_type_task", raise_if_not_found=False
            )
            if item_type and item_type.active:
                projects_to_default.write({"agile_default_item_type_id": item_type.id})
        self._ensure_agile_sequence()
        return result

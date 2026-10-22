from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain


class ProjectTask(models.Model):
    _inherit = "project.task"

    agile_tracks_environments = fields.Boolean(
        compute="_compute_agile_tracks_environments",
        store=True,
    )
    agile_environment_status_ids = fields.One2many(
        "project.task.environment.status",
        "task_id",
        copy=False,
        string="Environment Statuses",
    )
    agile_done_environment_id = fields.Many2one(
        "project.agile.environment",
        compute="_compute_environment_search",
        search="_search_done_environments",
        string="Done in environment",
    )
    agile_pending_environment_id = fields.Many2one(
        "project.agile.environment",
        compute="_compute_environment_search",
        search="_search_pending_environments",
        string="Not done in environment",
    )

    @api.depends(
        "project_id.agile_enabled",
        "project_id.is_template",
        "has_template_ancestor",
        "agile_item_type_id.tracks_environments",
    )
    def _compute_agile_tracks_environments(self):
        for task in self:
            task.agile_tracks_environments = bool(
                task.project_id.agile_enabled
                and not task.project_id.is_template
                and not task.has_template_ancestor
                and task.agile_item_type_id.tracks_environments
            )

    def _compute_environment_search(self):
        # Search-only native many2one selectors let users choose client-specific IDs.
        for task in self:
            task.agile_done_environment_id = False
            task.agile_pending_environment_id = False

    @api.model
    def _search_pending_environments(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        inverse = "not in" if operator == "in" else "in"
        return self._search_done_environments(inverse, value)

    @api.model
    def _search_done_environments(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        done = Domain(
            "agile_environment_status_ids",
            "any",
            [
                ("applicable", "=", True),
                ("environment_id", "in", value),
                ("status", "in", ["done", "verified"]),
            ],
        )
        if operator == "in":
            return done
        # Missing lines are not completion, but foreign/nontracking work is not a gap.
        return (
            Domain("agile_tracks_environments", "=", True)
            & Domain(
                "project_id.agile_environment_ids",
                "any",
                [
                    ("id", "in", value),
                    ("active", "=", True),
                ],
            )
            & ~done
        )

    def _sync_environment_statuses(self):
        tasks = self.filtered("agile_tracks_environments")
        tasks.check_access("write")
        tasks.project_id.check_access("read")
        status_model = self.env["project.task.environment.status"]
        # Enumerate identities completely; do not duplicate a line hidden by a rule.
        existing = status_model.sudo().search([("task_id", "in", tasks.ids)])
        pairs = {(line.task_id.id, line.environment_id.id) for line in existing}
        values = []
        for task in tasks:
            for environment in task.project_id.agile_environment_ids.filtered("active"):
                if (task.id, environment.id) not in pairs:
                    values.append(
                        {"task_id": task.id, "environment_id": environment.id}
                    )
        if values:
            context = {
                key: value
                for key, value in self.env.context.items()
                if not key.startswith("default_")
            }
            # Replace, rather than merge, to remove the Task form's default hints.
            # pylint: disable-next=context-overridden
            status_model.with_context(context).create(values)

    @api.model
    def _check_environment_derived_input(self, values):
        derived = {
            "agile_tracks_environments",
            "agile_done_environment_id",
            "agile_pending_environment_id",
        }
        defaults = {
            key.removeprefix("default_")
            for key in self.env.context
            if key.startswith("default_")
        }
        if derived & (values.keys() | defaults):
            raise AccessError(
                self.env._(
                    "Environment eligibility is derived from the Project and item type."
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            self._check_environment_derived_input(values)
        tasks = super().create(vals_list)
        tasks._sync_environment_statuses()
        return tasks

    def write(self, values):
        self._check_environment_derived_input(values)
        result = super().write(values)
        if {
            "project_id",
            "agile_item_type_id",
            "active",
            "state",
            "is_template",
            "parent_id",
        } & values.keys():
            affected = self.with_context(active_test=False)
            (affected | affected._get_all_subtasks())._sync_environment_statuses()
        return result

    @api.constrains("project_id")
    def _check_environment_history_project(self):
        for task in self:
            if any(
                line.environment_id.project_id != task.project_id
                for line in task.agile_environment_status_ids
            ):
                raise ValidationError(
                    self.env._(
                        "Copy tasks with environment history into another Project."
                    )
                )

    def action_environment_history(self):
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Environment history"),
            "res_model": "project.task.environment.status",
            "view_mode": "list,form",
            "domain": [("task_id", "=", self.id)],
            "context": {"create": False},
        }

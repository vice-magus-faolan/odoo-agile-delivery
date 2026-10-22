from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    agile_environment_ids = fields.One2many(
        "project.agile.environment",
        "project_id",
        string="Environments",
        copy=False,
        context={"active_test": False},
    )

    def _check_agile_configuration(self, values):
        if "agile_environment_ids" in values:
            super()._check_agile_configuration({"agile_enabled": False})
        return super()._check_agile_configuration(values)

    def _sync_open_environment_tasks(self):
        tasks = (
            self.env["project.task"]
            .sudo()
            .search(
                [
                    ("project_id", "in", self.ids),
                    ("agile_tracks_environments", "=", True),
                    ("state", "not in", ["1_done", "1_canceled"]),
                ]
            )
            .with_env(self.env)
        )
        # Configuration cannot report success after silently omitting hidden work.
        tasks._sync_environment_statuses()

    def write(self, values):
        result = super().write(values)
        if values.get("agile_enabled") or values.get("is_template", True) is False:
            self._sync_open_environment_tasks()
        return result

from odoo import fields, models


class ProjectAgileItemType(models.Model):
    _inherit = "project.agile.item.type"

    tracks_environments = fields.Boolean()

    def write(self, values):
        result = super().write(values)
        if values.get("tracks_environments"):
            tasks = (
                self.env["project.task"]
                .sudo()
                .search(
                    [
                        ("agile_item_type_id", "in", self.ids),
                        ("agile_tracks_environments", "=", True),
                        ("state", "not in", ["1_done", "1_canceled"]),
                    ]
                )
                .with_env(self.env)
            )
            tasks._sync_environment_statuses()
        return result

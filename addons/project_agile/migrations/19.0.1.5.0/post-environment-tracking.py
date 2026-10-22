from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for code in ("configuration", "data_import"):
        item_type = env.ref("project_agile.project_agile_item_type_" + code)
        item_type.write({"tracks_environments": True})
    env["project.project"].with_context(active_test=False).search(
        [
            ("agile_enabled", "=", True),
        ]
    )._sync_open_environment_tasks()

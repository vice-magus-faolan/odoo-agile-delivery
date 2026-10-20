from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    projects = (
        env["project.project"]
        .with_context(active_test=False)
        .search([("agile_enabled", "=", True)])
    )
    projects._agile_unkeyed_tasks()._assign_agile_keys()

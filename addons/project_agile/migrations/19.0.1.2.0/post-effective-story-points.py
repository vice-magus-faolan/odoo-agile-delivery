from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    tasks = env["project.task"].with_context(active_test=False).search([])
    field = tasks._fields["agile_effective_story_points"]
    env.add_to_compute(field, tasks)
    env.flush_all()

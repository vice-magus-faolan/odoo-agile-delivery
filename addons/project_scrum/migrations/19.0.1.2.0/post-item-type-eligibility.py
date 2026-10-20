from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Core creates the new seeds before the already-installed Scrum field loads.
    # Initialize only these newly introduced types, not existing client policies.
    env = api.Environment(cr, SUPERUSER_ID, {})
    for code in ("configuration", "data_import"):
        item_type = env.ref("project_agile.project_agile_item_type_" + code)
        item_type.write({"can_schedule_in_sprint": True})

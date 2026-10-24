from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Existing noupdate seeds are not reloaded; seed this newly introduced field once.
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("project_agile.project_agile_item_type_story").write(
        {
            "new_description_template": (
                "<p>As a ...</p><p>I want ...</p><p>so that ...</p>"
            )
        }
    )

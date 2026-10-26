from odoo import SUPERUSER_ID, api
from odoo.tools import file_open


def migrate(cr, version):
    # Existing noupdate seeds are not reloaded; initialize the new field once.
    env = api.Environment(cr, SUPERUSER_ID, {})
    story = env.ref(
        "project_agile.project_agile_item_type_story", raise_if_not_found=False
    )
    if story:
        with file_open("project_agile/data/story_description.html") as seed:
            story.new_description_template = seed.read()

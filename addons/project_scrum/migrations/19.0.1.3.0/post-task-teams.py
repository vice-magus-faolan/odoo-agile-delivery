"""Initialize ownership of already assigned work without changing Sprint history."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    tasks = (
        env["project.task"]
        .with_context(active_test=False)
        .search(
            [
                ("sprint_id", "!=", False),
                ("agile_team_id", "=", False),
            ]
        )
    )
    for team, assigned in tasks.grouped("sprint_id.team_id").items():
        assigned.write({"agile_team_id": team.id})

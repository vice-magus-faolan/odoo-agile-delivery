"""Native Odoo browser-harness coverage for the Agile planning board."""

from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestProjectAgilePlanningBoardHoot(HttpCase):
    """Run only this addon's Hoot tests through Odoo's supported test route."""

    def test_planning_board_hoot(self):
        self.browser_js(
            "/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&filter=project_agile_ui",
            "",
            "",
            login="admin",
            timeout=120,
            success_signal="[HOOT] Test suite succeeded",
        )

    def test_real_board_pagination_beyond_every_initial_window(self):
        user = mail_new_test_user(
            self.env, "page_tour_planner", groups="project.group_project_user"
        )
        project = self.env["project.project"].create(
            {
                "name": "Pagination tour",
                "agile_enabled": True,
                "agile_key": "PAGETOUR",
                "privacy_visibility": "employees",
            }
        )
        teams = self.env["project.agile.team"].create(
            [
                {"name": f"Tour team {i:03}", "project_id": project.id}
                for i in range(101)
            ]
        )
        sprints = self.env["project.sprint"].create(
            [
                {
                    "name": f"Tour Sprint {i:03}",
                    "project_id": project.id,
                    "team_id": teams[0].id,
                }
                for i in range(21)
            ]
        )
        item_type = self.env["project.agile.item.type"].create(
            {
                "name": "Pagination story",
                "code": "pagination_tour_story",
                "can_schedule_in_sprint": True,
            }
        )
        self.env["project.task"].create(
            [
                {
                    "name": f"Tour {kind} {i:03}",
                    "project_id": project.id,
                    "agile_item_type_id": item_type.id,
                    "agile_backlog_sequence": i,
                    "sprint_id": sprints[-1].id if kind == "assigned" else False,
                }
                for kind in ("assigned", "backlog")
                for i in range(101)
            ]
        )
        action = self.env["ir.actions.client"].create(
            {
                "name": "Pagination tour",
                "tag": "project_agile_ui.planning",
                "context": repr({"project_id": project.id}),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}", "agile_planning_pages", login=user.login
        )

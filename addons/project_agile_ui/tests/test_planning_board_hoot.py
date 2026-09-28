"""Native Odoo browser-harness coverage for the Agile planning board."""

from odoo.tests import HttpCase, tagged


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

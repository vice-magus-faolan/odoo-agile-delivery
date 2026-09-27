from odoo import Command
from odoo.tests.common import TransactionCase


class TestProjectSprintDocumentPage(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Scrum documentation project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "DOC",
            }
        )
        self.team = self.env["project.agile.team"].create(
            {"name": "Documentation team", "project_id": self.project.id}
        )
        self.sprint = self.env["project.sprint"].create(
            {
                "name": "Sprint 1",
                "project_id": self.project.id,
                "team_id": self.team.id,
                "task_ids": [Command.clear()],
            }
        )

    def test_create_retrospective_is_explicit_and_idempotent(self):
        self.assertFalse(self.sprint.retrospective_page_id)

        first_action = self.sprint.action_create_retrospective_page()
        second_action = self.sprint.action_create_retrospective_page()

        self.assertEqual(first_action["res_id"], self.sprint.retrospective_page_id.id)
        self.assertEqual(second_action["res_id"], self.sprint.retrospective_page_id.id)
        self.assertEqual(self.sprint.retrospective_page_id.type, "content")

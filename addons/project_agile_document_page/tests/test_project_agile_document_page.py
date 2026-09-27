from odoo.tests.common import TransactionCase


class TestProjectAgileDocumentPage(TransactionCase):
    def test_agile_project_creates_documentation_root_only_on_explicit_action(self):
        project = self.env["project.project"].create(
            {
                "name": "Engineering",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "ENG",
            }
        )

        self.assertFalse(project.agile_documentation_page_id)

        action = project.action_create_agile_documentation_root()

        page = project.agile_documentation_page_id
        self.assertTrue(page)
        self.assertEqual(page.project_id, project)
        self.assertEqual(page.type, "content")
        self.assertEqual(action["res_id"], page.id)

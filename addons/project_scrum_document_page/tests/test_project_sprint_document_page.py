from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestProjectSprintDocumentPage(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "Scrum documentation project", "privacy_visibility": "employees", "agile_enabled": True, "agile_key": "DOC"})
        self.team = self.env["project.agile.team"].create({"name": "Documentation team", "project_id": self.project.id})
        self.sprint = self.env["project.sprint"].create({"name": "Sprint 1", "project_id": self.project.id, "team_id": self.team.id, "task_ids": [Command.clear()]})

    def test_create_retrospective_is_explicit_idempotent_and_template_based(self):
        self.assertFalse(self.sprint.retrospective_page_id)
        first_action = self.sprint.action_create_retrospective_page()
        second_action = self.sprint.action_create_retrospective_page()
        page = self.sprint.retrospective_page_id
        self.assertEqual(first_action["res_id"], page.id)
        self.assertEqual(second_action["res_id"], page.id)
        self.assertEqual(page.type, "content")
        self.assertEqual(page.project_id, self.project)
        self.assertIn("Sprint Goal", page.content)

    def test_templates_are_global_categories_and_release_notes_are_unbound(self):
        for xml_id in ("document_page_category_adr", "document_page_category_sprint_retrospective", "document_page_category_runbook", "document_page_category_release_notes"):
            page = self.env.ref(f"project_scrum_document_page.{xml_id}")
            self.assertEqual(page.type, "category")
            self.assertFalse(page.company_id)
            self.assertTrue(page.template)
            self.assertFalse(page.project_id)

    def test_rejects_cross_project_and_archived_pages(self):
        other = self.env["project.project"].create({"name": "Other", "privacy_visibility": "employees", "agile_enabled": True, "agile_key": "OTH"})
        page = self.env["document.page"].create({"name": "Other page", "type": "content", "project_id": other.id, "company_id": other.company_id.id})
        with self.assertRaises(ValidationError):
            self.sprint.write({"retrospective_page_id": page.id})
        self.sprint.action_create_retrospective_page()
        self.sprint.retrospective_page_id.write({"active": False})
        with self.assertRaises(UserError):
            self.sprint.action_open_retrospective_page()

    def test_clear_and_delete_do_not_reparent_or_delete_pages(self):
        self.sprint.action_create_retrospective_page()
        page = self.sprint.retrospective_page_id
        self.sprint.action_clear_retrospective_page()
        self.assertTrue(page.exists())
        self.assertTrue(page.parent_id)
        self.sprint.write({"retrospective_page_id": page.id})
        page.unlink()
        self.sprint.invalidate_recordset(["retrospective_page_id"])
        self.assertFalse(self.sprint.retrospective_page_id)

    def test_closed_sprint_rejects_link_changes_but_can_open_existing_page(self):
        self.sprint.action_create_retrospective_page()
        self.sprint.action_start()
        self.sprint.action_close()
        with self.assertRaises(UserError):
            self.sprint.action_clear_retrospective_page()
        self.assertEqual(self.sprint.action_open_retrospective_page()["res_id"], self.sprint.retrospective_page_id.id)

    def test_non_editor_manager_cannot_create_a_retrospective(self):
        manager = mail_new_test_user(self.env, "Retrospective manager", groups="project.group_project_manager,document_knowledge.group_document_user")
        with self.assertRaises(AccessError):
            self.sprint.with_user(manager).action_create_retrospective_page()
        self.assertFalse(self.sprint.retrospective_page_id)

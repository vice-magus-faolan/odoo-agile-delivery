from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestProjectAgileDocumentPage(TransactionCase):
    def setUp(self):
        super().setUp()
        self.page_model = self.env["document.page"]
        self.project = self._create_agile_project("Engineering", "ENG")
        self.other_project = self._create_agile_project("Operations", "OPS")

    def _create_agile_project(self, name, key, **values):
        return self.env["project.project"].create(
            {
                "name": name,
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": key,
                **values,
            }
        )

    def _create_page(self, project, **values):
        return self.page_model.create(
            {
                "name": f"{project.name} documentation",
                "type": "content",
                "project_id": project.id,
                "company_id": project.company_id.id,
                **values,
            }
        )

    def test_agile_project_creates_documentation_root_only_on_explicit_action(self):
        self.assertFalse(self.project.agile_documentation_page_id)

        action = self.project.action_create_agile_documentation_root()

        page = self.project.agile_documentation_page_id
        self.assertTrue(page)
        self.assertEqual(page.project_id, self.project)
        self.assertEqual(page.type, "content")
        self.assertEqual(action["res_id"], page.id)

    def test_non_admin_cannot_create_a_documentation_root_without_page_create_access(
        self,
    ):
        employee = mail_new_test_user(
            self.env,
            "Agile documentation employee",
            groups="project.group_project_manager,document_knowledge.group_document_user",
        )
        with self.assertRaises(AccessError):
            self.project.with_user(employee).action_create_agile_documentation_root()

        self.assertFalse(self.project.agile_documentation_page_id)

    def test_rejects_a_page_from_a_different_company(self):
        other_company = self.env["res.company"].create({"name": "Other Company"})
        page = self._create_page(self.project, company_id=other_company.id)

        with self.assertRaises(ValidationError):
            self.project.write({"agile_documentation_page_id": page.id})

        self.assertFalse(self.project.agile_documentation_page_id)

    def test_rejects_archived_pages_when_linking_and_opening(self):
        archived_page = self._create_page(self.project, active=False)
        with self.assertRaises(ValidationError):
            self.project.write({"agile_documentation_page_id": archived_page.id})

        self.project.action_create_agile_documentation_root()
        linked_page = self.project.agile_documentation_page_id
        linked_page.write({"active": False})
        with self.assertRaises(UserError):
            self.project.action_open_agile_documentation_root()

    def test_rejects_a_page_owned_by_another_project(self):
        page = self._create_page(self.other_project)

        with self.assertRaises(ValidationError):
            self.project.write({"agile_documentation_page_id": page.id})

        self.assertFalse(self.project.agile_documentation_page_id)

    def test_rejects_documentation_roots_on_ordinary_projects(self):
        project = self.env["project.project"].create(
            {"name": "Ordinary", "privacy_visibility": "employees"}
        )
        page = self._create_page(project)

        with self.assertRaises(ValidationError):
            project.write({"agile_documentation_page_id": page.id})
        with self.assertRaises(UserError):
            project.action_create_agile_documentation_root()

        self.assertFalse(project.agile_documentation_page_id)

    def test_multi_record_write_rolls_back_an_invalid_documentation_root_batch(self):
        first = self._create_agile_project("First", "FIRST")
        second = self._create_agile_project("Second", "SECOND")
        page = self._create_page(first)

        with self.assertRaises(ValidationError):
            (first | second).write({"agile_documentation_page_id": page.id})

        self.assertFalse(first.agile_documentation_page_id)
        self.assertFalse(second.agile_documentation_page_id)

    def test_clearing_the_root_does_not_delete_or_reparent_the_page(self):
        self.project.action_create_agile_documentation_root()
        page = self.project.agile_documentation_page_id

        self.project.action_clear_agile_documentation_root()

        self.assertFalse(self.project.agile_documentation_page_id)
        self.assertTrue(page.exists())
        self.assertEqual(page.project_id, self.project)
        self.assertTrue(page.active)

    def test_deleting_the_page_clears_only_the_optional_bridge_relation(self):
        self.project.action_create_agile_documentation_root()
        page = self.project.agile_documentation_page_id

        page.unlink()
        self.project.invalidate_recordset(["agile_documentation_page_id"])

        self.assertFalse(self.project.agile_documentation_page_id)

    def test_open_rejects_a_root_mutated_to_a_non_content_page(self):
        self.project.action_create_agile_documentation_root()
        page = self.project.agile_documentation_page_id
        page.write({"type": "category"})

        with self.assertRaises(UserError):
            self.project.action_open_agile_documentation_root()

    def test_inaccessible_page_is_not_opened_through_the_project_bridge(self):
        employee = mail_new_test_user(
            self.env,
            "Agile documentation reader",
            groups="project.group_project_user,document_knowledge.group_document_user",
        )
        self.project.action_create_agile_documentation_root()
        page = self.project.agile_documentation_page_id
        other_company = self.env["res.company"].create({"name": "Restricted Company"})
        page.write({"company_id": other_company.id})

        with self.assertRaises(AccessError):
            self.project.with_user(employee).action_open_agile_documentation_root()

    def test_ordinary_project_view_hides_the_optional_bridge(self):
        ordinary_project = self.env["project.project"].create(
            {"name": "Ordinary", "privacy_visibility": "employees"}
        )
        view = self.env.ref(
            "project_agile_document_page.view_project_form_agile_document_page"
        )

        self.assertFalse(ordinary_project.agile_documentation_page_id)
        self.assertIn('invisible="not agile_enabled"', view.arch_db)

    def test_open_requires_a_documentation_root(self):
        with self.assertRaises(UserError):
            self.project.action_open_agile_documentation_root()

    def test_category_template_initializes_a_new_page(self):
        category = self.page_model.create(
            {
                "name": "Fixture category",
                "type": "category",
                "template": "<p>Fixture template</p>",
            }
        )
        page = self.page_model.new({"name": "Fixture draft", "parent_id": category.id})
        page._onchange_parent_id()
        self.assertEqual(page.content, category.template)

    def test_content_history_archive_and_cascade_deletion(self):
        page = self._create_page(
            self.project,
            content="<p>Initial fixture content</p>",
            draft_name="1.0",
            draft_summary="Initial fixture history",
        )
        page.content = "<p>Updated fixture content</p>"
        self.assertTrue(page.history_head)
        self.assertEqual(len(page.history_ids), 2)
        history = page.history_ids
        page.active = False
        self.assertFalse(page.active)
        page.unlink()
        self.assertFalse(page.exists())
        self.assertFalse(history.exists())

    def test_project_document_page_relation_and_actions(self):
        page = self._create_page(self.project)
        self.assertIn(page, self.project.document_page_ids)
        self.assertEqual(self.project.document_page_count, 1)
        for xmlid in (
            "document_page.view_wiki_form",
            "document_page.view_wiki_tree",
            "document_page.view_wiki_filter",
            "document_page_project.action_document_page_projects",
            "document_knowledge.group_document_user",
            "document_page.group_document_editor",
            "document_page.group_document_manager",
            "document_page.document_page_rule",
            "document_page.document_page_history_rule",
        ):
            self.assertTrue(self.env.ref(xmlid))

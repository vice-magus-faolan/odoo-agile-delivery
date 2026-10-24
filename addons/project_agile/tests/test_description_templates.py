from odoo.exceptions import AccessError
from odoo.tests import Form
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestDescriptionTemplates(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.story = cls.env.ref("project_agile.project_agile_item_type_story")
        cls.task_type = cls.env.ref("project_agile.project_agile_item_type_task")
        cls.member = mail_new_test_user(
            cls.env, "template_member", groups="project_agile.group_agile_member"
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Template client",
                "agile_enabled": True,
                "agile_key": "TEXT",
                "privacy_visibility": "employees",
                "agile_default_item_type_id": cls.story.id,
            }
        )
        cls.tasks = cls.env["project.task"].with_user(cls.member)

    def _create(self, **values):
        return self.tasks.create(
            {"name": "New work", "project_id": self.project.id, **values}
        )

    def test_seed_defaults_and_explicit_content(self):
        self.assertIn("As a", self.story.new_description_template)
        self.assertIn("I want", self.story.new_description_template)
        self.assertIn("so that", self.story.new_description_template)
        self.assertEqual(
            self._create().description, self.story.new_description_template
        )
        self.assertFalse(self._create(agile_item_type_id=self.task_type.id).description)
        self.assertFalse(self._create(description=False).description)
        self.assertEqual(
            self._create(description="<p>Exact</p>").description, "<p>Exact</p>"
        )
        context = self.tasks.with_context(
            default_project_id=self.project.id, default_description=False
        )
        self.assertFalse(context.create({"name": "Explicit blank default"}).description)
        self.assertFalse(
            context.default_get(["description", "agile_item_type_id"])["description"]
        )

    def test_configuration_changes_only_future_work(self):
        old = self._create()
        original = old.description
        self.story.new_description_template = "<p>Edited starting point</p>"
        self.assertEqual(
            self._create().description, self.story.new_description_template
        )
        self.story.new_description_template = False
        self.assertFalse(self._create().description)
        old.write({"agile_item_type_id": self.task_type.id})
        self.assertEqual(old.description, original)
        with self.assertRaises(AccessError):
            self.story.with_user(self.member).write(
                {"new_description_template": "Denied"}
            )

    def test_native_form_defaults_and_type_choice(self):
        with Form(self.tasks.with_context(default_project_id=self.project.id)) as form:
            form.name = "Form Story"
            self.assertEqual(form.description, self.story.new_description_template)
        self.assertEqual(form.record.description, self.story.new_description_template)
        self.project.agile_default_item_type_id = self.task_type
        with Form(self.tasks.with_context(default_project_id=self.project.id)) as form:
            form.name = "Selected Story"
            form.agile_item_type_id = self.story
            self.assertEqual(form.description, self.story.new_description_template)
        with Form(form.record) as existing:
            existing.description = "<p>Written content</p>"
            existing.agile_item_type_id = self.task_type
        self.assertEqual(form.record.description, "<p>Written content</p>")

    def test_plain_project_move_and_copy_preserve_content(self):
        plain = self.env["project.project"].create(
            {"name": "Plain", "privacy_visibility": "employees"}
        )
        work = self.tasks.create(
            {
                "name": "Plain work",
                "project_id": plain.id,
                "agile_item_type_id": self.story.id,
            }
        )
        self.assertFalse(work.description)
        work.write({"project_id": self.project.id})
        self.assertFalse(work.description)
        source = self._create(description="<p>Original work</p>")
        self.assertEqual(source.copy().description, source.description)

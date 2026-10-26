import importlib.util

from odoo.exceptions import AccessError
from odoo.tests import Form
from odoo.tests.common import TransactionCase
from odoo.tools import file_path

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

    def test_pristine_draft_type_switch_and_save(self):
        bug = self.env.ref("project_agile.project_agile_item_type_bug")
        bug.new_description_template = "<p>Bug starting point</p>"
        tasks = self.tasks.with_context(default_project_id=self.project.id)
        with Form(tasks) as form:
            form.name = "Draft Story becomes Task"
            self.assertEqual(form.description, self.story.new_description_template)
            form.agile_item_type_id = self.task_type
            self.assertFalse(form.description)
        self.assertFalse(form.record.description)
        with Form(tasks) as form:
            form.name = "Draft switches templates"
            form.agile_item_type_id = bug
            self.assertEqual(form.description, bug.new_description_template)
        self.assertEqual(form.record.description, bug.new_description_template)
        with Form(tasks) as form:
            form.name = "Authored draft"
            form.description = "<p>Author text</p>"
            form.agile_item_type_id = self.task_type
        self.assertEqual(form.record.description, "<p>Author text</p>")
        for explicit in (False, self.story.new_description_template):
            with Form(tasks.with_context(default_description=explicit)) as form:
                form.name = "Explicit draft"
                form.agile_item_type_id = bug
            self.assertEqual(form.record.description, explicit)
        saved = self._create()
        original = saved.description
        with Form(saved) as form:
            form.agile_item_type_id = self.task_type
        self.assertEqual(saved.description, original)

    def _description_migration(self):
        spec = importlib.util.spec_from_file_location(
            "description_template_migration",
            file_path(
                "project_agile/migrations/19.0.1.7.0/post-description-template.py"
            ),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.migrate

    def test_migration_uses_install_seed(self):
        original = self.story.new_description_template
        self.story.new_description_template = False
        migrate = self._description_migration()
        migrate(self.cr, "19.0.1.6.0")
        self.assertEqual(self.story.new_description_template, original)

    def test_migration_skips_missing_story(self):
        original = self.story.new_description_template
        migrate = self._description_migration()
        self.env["ir.model.data"].search(
            [
                ("module", "=", "project_agile"),
                ("name", "=", "project_agile_item_type_story"),
            ]
        ).unlink()
        migrate(self.cr, "19.0.1.6.0")
        self.assertEqual(self.story.new_description_template, original)

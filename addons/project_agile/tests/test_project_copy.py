from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestProjectCopy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = mail_new_test_user(
            cls.env, "copy_manager", groups="project.group_project_manager"
        )
        cls.member = mail_new_test_user(
            cls.env, "copy_member", groups="project_agile.group_agile_member"
        )
        cls.item_type = cls.env.ref(
            "project_agile.project_agile_item_type_configuration"
        )
        cls.item_type.allowed_child_type_ids = [Command.link(cls.item_type.id)]
        cls.source = cls.env["project.project"].create(
            {
                "name": "Client rollout",
                "privacy_visibility": "employees",
                "company_id": cls.env.company.id,
                "agile_enabled": True,
                "agile_key": "COPYORIGIN",
                "agile_default_item_type_id": cls.item_type.id,
                "agile_estimation_method": "fibonacci",
                "agile_environment_ids": [
                    Command.create(
                        {"name": "Production", "sequence": 40, "is_production": True}
                    ),
                    Command.create({"name": "UAT", "sequence": 10}),
                    Command.create(
                        {"name": "Retired", "sequence": 20, "is_production": True}
                    ),
                ],
            }
        )
        cls.root = cls.env["project.task"].create(
            {"name": "Configure client", "project_id": cls.source.id}
        )
        cls.child = cls.env["project.task"].create(
            {
                "name": "Nested configuration",
                "project_id": cls.source.id,
                "parent_id": cls.root.id,
            }
        )
        cls.lines = (cls.root | cls.child).agile_environment_status_ids
        cls.lines.with_user(cls.member).write({"status": "verified"})
        cls.source.agile_environment_ids.filtered(
            lambda environment: environment.name == "Retired"
        ).active = False

    def _environment_settings(self, project):
        return [
            (row.name, row.sequence, row.active, row.is_production)
            for row in project.agile_environment_ids
        ]

    def _check_native_copy(self, from_template):
        if from_template:
            action = self.source.with_user(
                self.manager
            ).action_create_template_from_project()
            source = self.env["project.project"].browse(action["params"]["project_id"])
            self.assertTrue(source.is_template)
            self.assertTrue(source.agile_enabled)
            self.assertNotEqual(source.agile_key, self.source.agile_key)
            self.assertEqual(
                self._environment_settings(source),
                self._environment_settings(self.source),
            )
            self.assertFalse(any(source.task_ids.mapped("agile_key")))
            self.assertFalse(source.task_ids.agile_environment_status_ids)
        else:
            source = self.source
        source_tasks = self.env["project.task"].search([("project_id", "=", source.id)])
        task_fields = ["name", "project_id", "parent_id", "agile_key"]
        task_snapshot = source_tasks.read(task_fields, load=None)
        history_fields = [
            "task_id",
            "environment_id",
            "status",
            "actor_id",
            "changed_at",
        ]
        history_snapshot = self.lines.read(history_fields, load=None)
        settings = self._environment_settings(source)
        self.assertEqual(
            settings,
            [
                ("UAT", 10, True, False),
                ("Retired", 20, False, True),
                ("Production", 40, True, True),
            ],
        )
        caller = source.with_user(self.manager)
        self.assertFalse(caller.env.su)
        destination = (
            caller.action_create_from_template() if from_template else caller.copy()
        )
        self.assertTrue(destination.agile_enabled)
        self.assertFalse(destination.is_template)
        self.assertTrue(destination.agile_key)
        self.assertNotIn(
            destination.agile_key, [source.agile_key, self.source.agile_key]
        )
        self.assertEqual(destination.agile_estimation_method, "fibonacci")
        self.assertEqual(destination.agile_default_item_type_id, self.item_type)
        self.assertEqual(destination.company_id, source.company_id)
        self.assertEqual(self._environment_settings(destination), settings)
        environments = destination.agile_environment_ids
        self.assertFalse(environments & source.agile_environment_ids)
        self.assertEqual(environments.project_id, destination)
        self.assertEqual(environments.company_id, destination.company_id)
        tasks = self.env["project.task"].search([("project_id", "=", destination.id)])
        self.assertEqual(len(tasks), 2)
        self.assertEqual(set(tasks.mapped("name")), set(source_tasks.mapped("name")))
        self.assertFalse(tasks & source_tasks)
        self.assertEqual(tasks.company_id, destination.company_id)
        keys = set(tasks.mapped("agile_key"))
        self.assertEqual(
            keys, {f"{destination.agile_key}-1", f"{destination.agile_key}-2"}
        )
        self.assertFalse(keys & set((self.root | self.child).mapped("agile_key")))
        child = tasks.filtered(lambda task: task.name == self.child.name)
        self.assertEqual(child.parent_id.name, self.root.name)
        self.assertIn(child.parent_id, tasks)
        lines = tasks.agile_environment_status_ids
        self.assertEqual(len(lines), 4)
        self.assertFalse(lines & self.lines)
        self.assertEqual(set(lines.mapped("status")), {"todo"})
        self.assertEqual(lines.actor_id, self.manager)
        self.assertEqual(lines.environment_id, environments.filtered("active"))
        self.assertEqual(lines.project_id, destination)
        self.assertFalse(lines.message_ids & self.lines.message_ids)
        followup = (
            self.env["project.task"]
            .with_user(self.manager)
            .create({"name": "Next client work", "project_id": destination.id})
        )
        self.assertEqual(followup.agile_key, f"{destination.agile_key}-3")
        self.assertEqual(followup.agile_item_type_id, self.item_type)
        self.assertEqual(source_tasks.read(task_fields, load=None), task_snapshot)
        self.assertEqual(self.lines.read(history_fields, load=None), history_snapshot)
        self.assertEqual(self._environment_settings(source), settings)
        self.assertEqual(
            self._environment_settings(self.source), self._environment_settings(source)
        )

    def test_duplicate_inherits_configuration_with_fresh_identity(self):
        self._check_native_copy(from_template=False)

    def test_template_creates_configuration_with_fresh_identity(self):
        self._check_native_copy(from_template=True)

    def test_explicit_defaults_and_plain_templates(self):
        caller = self.source.with_user(self.manager)
        copied = caller.copy(
            {
                "agile_key": "COPYEXPLICIT",
                "agile_default_item_type_id": False,
                "agile_estimation_method": "none",
                "agile_environment_ids": [Command.create({"name": "Pilot"})],
            }
        )
        self.assertEqual(copied.agile_key, "COPYEXPLICIT")
        self.assertFalse(copied.agile_default_item_type_id)
        self.assertEqual(copied.agile_estimation_method, "none")
        self.assertEqual(copied.agile_environment_ids.mapped("name"), ["Pilot"])
        disabled = caller.copy({"agile_enabled": False})
        self.assertFalse(disabled.agile_key)
        self.assertFalse(disabled.agile_environment_ids)
        self.assertFalse(any(disabled.task_ids.mapped("agile_key")))
        self.assertFalse(disabled.task_ids.agile_environment_status_ids)
        plain = self.env["project.project"].create(
            {"name": "Plain template", "is_template": True}
        )
        project = plain.with_user(self.manager).action_create_from_template()
        self.assertFalse(project.agile_enabled)
        self.assertFalse(project.agile_key)
        self.assertFalse(project.agile_environment_ids)

    def test_allocator_skips_archived_foreign_namespace(self):
        sequence = self.env.ref("project_agile.sequence_project_copy")
        sequence.write({"prefix": "COPYCOLLIDE", "number_next": 1})
        company = self.env["res.company"].create({"name": "Reserved key company"})
        hidden = (
            self.env["project.project"]
            .with_company(company)
            .create(
                {
                    "name": "Archived namespace",
                    "active": False,
                    "company_id": company.id,
                    "agile_enabled": True,
                    "agile_key": "COPYCOLLIDE1",
                }
            )
        )
        hidden = hidden.with_context(allowed_company_ids=self.manager.company_ids.ids)
        with self.assertRaises(AccessError):
            hidden.with_user(self.manager).check_access("read")
        copied = self.source.with_user(self.manager).copy()
        self.assertEqual(copied.agile_key, "COPYCOLLIDE2")
        self.assertEqual(copied.company_id, self.source.company_id)
        self.assertEqual(hidden.agile_key, "COPYCOLLIDE1")

    def test_copy_preserves_caller_and_company_boundaries(self):
        caller = self.source.with_user(self.member)
        caller.check_access("read")
        for record in (caller, caller.with_context(sudo=True)):
            with self.assertRaises(AccessError):
                record.copy()
        company = self.env["res.company"].create({"name": "Foreign copy company"})
        foreign = (
            self.env["project.project"]
            .with_company(company)
            .create(
                {
                    "name": "Foreign client",
                    "privacy_visibility": "employees",
                    "company_id": company.id,
                    "agile_enabled": True,
                    "agile_key": "COPYFOREIGN",
                    "agile_environment_ids": [Command.create({"name": "Foreign UAT"})],
                }
            )
        )
        foreign = foreign.with_context(allowed_company_ids=self.manager.company_ids.ids)
        for record in (
            foreign.with_user(self.manager),
            foreign.with_user(self.manager).with_context(sudo=True),
        ):
            with self.assertRaises(AccessError):
                record.copy()
        self.source.is_template = True
        with self.assertRaises(AccessError):
            self.source.with_user(self.member).action_create_from_template()
        foreign.is_template = True
        with self.assertRaises(AccessError):
            foreign.with_user(self.manager).action_create_from_template()

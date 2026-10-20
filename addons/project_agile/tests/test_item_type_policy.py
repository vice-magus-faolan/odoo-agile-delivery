from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestItemTypePolicy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env, "mixed_work_member", groups="project_agile.group_agile_member"
        )
        cls.story = cls.env.ref("project_agile.project_agile_item_type_story")
        cls.configuration = cls.env.ref(
            "project_agile.project_agile_item_type_configuration"
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Mixed client",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "MIXED",
                "agile_estimation_method": "fibonacci",
            }
        )
        cls.development = cls.env["project.task.type"].create(
            {
                "name": "Code review",
                "sequence": 1,
                "project_ids": [Command.set(cls.project.ids)],
                "agile_item_type_ids": [Command.set(cls.story.ids)],
            }
        )
        cls.business = cls.env["project.task.type"].create(
            {
                "name": "Waiting on client",
                "sequence": 2,
                "project_ids": [Command.set(cls.project.ids)],
                "agile_item_type_ids": [Command.set(cls.configuration.ids)],
            }
        )
        cls.shared = cls.env["project.task.type"].create(
            {
                "name": "Shared",
                "sequence": 10,
                "project_ids": [Command.set(cls.project.ids)],
            }
        )
        cls.tasks = cls.env["project.task"].with_user(cls.user)

    def _task(self, item_type, **values):
        return self.tasks.create(
            {
                "name": "Client work",
                "project_id": self.project.id,
                "agile_item_type_id": item_type.id,
                **values,
            }
        )

    def test_hours_and_points_share_project_without_losing_estimates(self):
        self.assertFalse(self.user.has_group("project.group_project_manager"))
        configuration = self._task(
            self.configuration, allocated_hours=4, agile_story_points=4
        )
        self.assertEqual(configuration.allocated_hours, 4)
        self.assertEqual(configuration.agile_effective_story_points, 0)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            configuration.write({"agile_item_type_id": self.story.id})
        self.assertEqual(configuration.agile_item_type_id, self.configuration)
        self.assertEqual(configuration.agile_story_points, 4)
        configuration.write(
            {"agile_story_points": 5, "agile_item_type_id": self.story.id}
        )
        self.assertEqual(configuration.agile_effective_story_points, 5)
        configuration.write({"agile_item_type_id": self.configuration.id})
        self.assertEqual(configuration.agile_story_points, 5)
        self.assertEqual(configuration.allocated_hours, 4)
        self.assertEqual(configuration.agile_effective_story_points, 0)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._task(self.story, agile_story_points=4)
        with self.assertRaises(AccessError):
            self.configuration.with_user(self.user).write({"uses_story_points": True})

    def test_create_drag_type_change_and_batch_rejection(self):
        story = self._task(self.story)
        self.assertEqual(story.stage_id, self.development)
        configuration = self._task(self.configuration)
        self.assertEqual(configuration.stage_id, self.business)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._task(self.configuration, stage_id=self.development.id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            (story | configuration).write(
                {"stage_id": self.development.id, "name": "Must rollback"}
            )
        self.assertEqual(configuration.stage_id, self.business)
        self.assertEqual(story.name, "Client work")
        story.write({"agile_item_type_id": self.configuration.id})
        self.assertEqual(story.stage_id, self.business)
        story.write({"stage_id": self.shared.id})
        story.write({"agile_item_type_id": self.story.id})
        self.assertEqual(story.stage_id, self.shared)
        self.assertFalse(self.tasks.search_count([("name", "=", "Must rollback")]))
        before = self.tasks.search_count([("project_id", "=", self.project.id)])
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.tasks.create(
                [
                    {
                        "name": "Batch valid",
                        "project_id": self.project.id,
                        "agile_item_type_id": self.story.id,
                    },
                    {
                        "name": "Batch invalid",
                        "project_id": self.project.id,
                        "agile_item_type_id": self.configuration.id,
                        "stage_id": self.development.id,
                    },
                ]
            )
        self.assertEqual(
            self.tasks.search_count([("project_id", "=", self.project.id)]), before
        )

    def test_stage_policy_archived_work_and_native_project_links(self):
        task = self._task(self.configuration)
        task.write({"active": False})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.business.write({"agile_item_type_ids": [Command.set(self.story.ids)]})
        other = self.env["project.project"].create({"name": "Other"})
        foreign = self.env["project.task.type"].create(
            {"name": "Foreign", "project_ids": [Command.set(other.ids)]}
        )
        task.write({"stage_id": foreign.id})
        self.assertEqual(task.stage_id, foreign)
        foreign.write({"project_ids": [Command.clear()]})
        self.assertEqual(task.stage_id, foreign)

    def test_no_compatible_stage_and_native_untyped_work(self):
        self.shared.write({"agile_item_type_ids": [Command.set(self.story.ids)]})
        self.business.write({"agile_item_type_ids": [Command.set(self.story.ids)]})
        configuration = self._task(self.configuration)
        self.assertFalse(configuration.stage_id)
        untyped = self.tasks.create(
            {
                "name": "Unmanaged",
                "project_id": self.project.id,
                "agile_item_type_id": False,
                "stage_id": self.development.id,
            }
        )
        self.assertFalse(untyped.agile_item_type_id)
        ordinary = self.env["project.project"].create(
            {"name": "Ordinary", "privacy_visibility": "employees"}
        )
        native = self.tasks.create(
            {
                "name": "Native",
                "project_id": ordinary.id,
                "agile_item_type_id": self.configuration.id,
            }
        )
        self.assertFalse(native.agile_key)

    def test_project_and_context_quick_defaults_respect_explicit_and_archived_choices(
        self,
    ):
        task_type = self.env.ref("project_agile.project_agile_item_type_task")
        self.assertEqual(self.project.agile_default_item_type_id, task_type)
        quick = self.tasks.with_context(default_project_id=self.project.id).create(
            {"name": "Quick"}
        )
        self.assertEqual(quick.agile_item_type_id, task_type)
        defaults = self.tasks.with_context(
            default_project_id=self.project.id
        ).default_get(["project_id", "agile_item_type_id"])
        self.assertEqual(defaults["agile_item_type_id"], task_type.id)
        explicit = self.tasks.with_context(
            default_project_id=self.project.id, default_agile_item_type_id=self.story.id
        ).create({"name": "Explicit"})
        self.assertEqual(explicit.agile_item_type_id, self.story)
        untyped = self.tasks.create(
            {
                "name": "Explicit none",
                "project_id": self.project.id,
                "agile_item_type_id": False,
            }
        )
        self.assertFalse(untyped.agile_item_type_id)
        task_type.write({"active": False})
        archived = self.tasks.create(
            {"name": "Archived default", "project_id": self.project.id}
        )
        self.assertFalse(archived.agile_item_type_id)
        new_project = self.env["project.project"].create(
            {
                "name": "No active default",
                "agile_enabled": True,
                "agile_key": "NODEFAULT",
            }
        )
        self.assertFalse(new_project.agile_default_item_type_id)

    def test_single_mixed_work_kind_and_native_group_expansion(self):
        model = self.tasks.with_context(
            default_project_id=self.project.id,
            project_kanban=True,
            read_group_expand=True,
        )
        base = [("project_id", "=", self.project.id)]

        def columns(domain):
            result = model.web_read_group(domain, ["stage_id"])
            return self.env["project.task.type"].browse(
                row["stage_id"][0] for row in result["groups"] if row["stage_id"]
            )

        single = columns(base + [("agile_item_type_id", "=", self.configuration.id)])
        self.assertIn(self.business, single)
        self.assertIn(self.shared, single)
        self.assertNotIn(self.development, single)
        mixed = columns(
            base
            + [("agile_item_type_id", "in", (self.configuration | self.story).ids)],
        )
        self.assertTrue((self.business | self.development | self.shared) <= mixed)
        hours = columns(
            base
            + [
                ("agile_item_type_id", "!=", False),
                ("agile_uses_story_points", "=", False),
            ],
        )
        self.assertNotIn(self.development, hours)
        self.assertIn(self.business, hours)
        points = columns(
            base
            + [
                ("agile_item_type_id", "!=", False),
                ("agile_uses_story_points", "=", True),
            ]
        )
        self.assertIn(self.development, points)
        self.assertNotIn(self.business, points)
        untyped_hours = columns(base + [("agile_uses_story_points", "=", False)])
        self.assertIn(self.development, untyped_hours)
        unknown_union = columns(
            base
            + [
                "|",
                ("agile_item_type_id", "=", self.configuration.id),
                ("name", "ilike", "Client"),
            ]
        )
        self.assertIn(self.development, unknown_union)
        unrestricted = columns(base)
        self.assertIn(self.development, unrestricted)
        native_union = columns(
            [
                "|",
                ("project_id", "=", self.project.id),
                ("agile_item_type_id", "=", self.configuration.id),
            ],
        )
        self.assertIn(self.development, native_union)

    def test_enabling_existing_projects_defaults_only_missing_choices(self):
        manager = mail_new_test_user(
            self.env, "enable_agile_manager", groups="project.group_project_manager"
        )
        task_type = self.env.ref("project_agile.project_agile_item_type_task")
        projects = (
            self.env["project.project"]
            .with_user(manager)
            .create(
                [
                    {"name": "Enable missing", "agile_key": "ENABLEMISSING"},
                    {
                        "name": "Enable chosen",
                        "agile_key": "ENABLECHOSEN",
                        "agile_default_item_type_id": self.story.id,
                    },
                ]
            )
        )
        projects.write({"agile_enabled": True})
        self.assertEqual(projects[0].agile_default_item_type_id, task_type)
        self.assertEqual(projects[1].agile_default_item_type_id, self.story)
        quick = self.tasks.with_context(default_project_id=projects[0].id).create(
            {"name": "Quick after enabling"}
        )
        self.assertEqual(quick.agile_item_type_id, task_type)
        explicit = self.env["project.project"].create(
            {"name": "Explicit none", "agile_key": "ENABLENONE"}
        )
        explicit.write({"agile_enabled": True, "agile_default_item_type_id": False})
        self.assertFalse(explicit.agile_default_item_type_id)
        explicit.write({"agile_enabled": True})
        self.assertFalse(explicit.agile_default_item_type_id)
        self.story.active = False
        retained = self.env["project.project"].create(
            {
                "name": "Archived choice",
                "agile_key": "ENABLEARCHIVED",
                "agile_default_item_type_id": self.story.id,
            }
        )
        retained.write({"agile_enabled": True})
        self.assertEqual(retained.agile_default_item_type_id, self.story)
        task_type.active = False
        missing = self.env["project.project"].create(
            {"name": "Archived seed", "agile_key": "ENABLEARCHIVEDSEED"}
        )
        missing.write({"agile_enabled": True})
        self.assertFalse(missing.agile_default_item_type_id)

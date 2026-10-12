from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestProjectAgileDomain(TransactionCase):
    def setUp(self):
        super().setUp()
        self.item_type_model = self.env["project.agile.item.type"]
        self.epic_type = self.item_type_model.create(
            {"name": "Epic", "code": "test_epic"}
        )
        self.story_type = self.item_type_model.create(
            {"name": "Story", "code": "test_story"}
        )
        self.task_type = self.item_type_model.create(
            {"name": "Task", "code": "test_task"}
        )
        self.epic_type.write(
            {"allowed_child_type_ids": [Command.set(self.story_type.ids)]}
        )
        self.story_type.write(
            {"allowed_child_type_ids": [Command.set(self.task_type.ids)]}
        )
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

    def _create_task(self, name, item_type=None, **values):
        return self.env["project.task"].create(
            {
                "name": name,
                "project_id": self.project.id,
                "agile_item_type_id": item_type.id if item_type else False,
                **values,
            }
        )

    def test_agile_task_receives_immutable_key(self):
        task = self._create_task("Implement key allocation")

        self.assertEqual(task.agile_key, "ENG-1")
        with self.assertRaises(ValidationError):
            task.write({"agile_key": "ENG-99"})

    def test_generated_keys_are_stable_and_unique(self):
        first = self._create_task("First")
        second = self._create_task("Second")

        self.assertEqual((first.agile_key, second.agile_key), ("ENG-1", "ENG-2"))
        first.write({"name": "Renamed"})
        self.assertEqual(first.agile_key, "ENG-1")
        with self.assertRaises(ValidationError):
            self.project.write({"agile_key": "NEW"})

    def test_non_agile_tasks_do_not_receive_keys_or_policy(self):
        project = self.env["project.project"].create(
            {"name": "Ordinary", "privacy_visibility": "employees"}
        )

        task = self.env["project.task"].create(
            {
                "name": "Ordinary task",
                "project_id": project.id,
                "agile_key": "FORCED-1",
                "agile_story_points": 13,
            }
        )

        self.assertFalse(task.agile_key)
        self.assertEqual(task.agile_story_points, 13)

    def test_parent_type_policy_and_project_isolation_are_enforced(self):
        parent = self._create_task("Epic", self.epic_type)
        child = self._create_task("Story", self.story_type, parent_id=parent.id)
        invalid_parent = self._create_task("Task", self.task_type)

        self.assertEqual(child.parent_id, parent)
        with self.assertRaises(ValidationError):
            invalid_parent.write({"parent_id": parent.id})

        foreign_child = self.env["project.task"].create(
            {
                "name": "Foreign story",
                "project_id": self.other_project.id,
                "agile_item_type_id": self.story_type.id,
            }
        )
        key_before = foreign_child.agile_key
        with self.assertRaises(ValidationError):
            foreign_child.write({"parent_id": parent.id})
        self.assertEqual(
            (foreign_child.project_id, foreign_child.agile_key),
            (self.other_project, key_before),
        )

    def test_keyed_task_cannot_move_to_another_project(self):
        task = self._create_task("Pinned work item")

        with self.assertRaises(ValidationError):
            task.write({"project_id": self.other_project.id})

        self.assertEqual((task.project_id, task.agile_key), (self.project, "ENG-1"))

    def test_type_policy_cannot_be_reconfigured_to_invalidate_tasks(self):
        parent = self._create_task("Epic", self.epic_type)
        self._create_task("Story", self.story_type, parent_id=parent.id)

        with self.assertRaises(ValidationError):
            self.epic_type.write({"allowed_child_type_ids": [Command.clear()]})

        self.assertIn(self.story_type, self.epic_type.allowed_child_type_ids)

    def test_native_task_cycle_protection_remains_active(self):
        parent = self._create_task("Untyped parent")
        child = self._create_task("Untyped child", parent_id=parent.id)

        with self.assertRaises(ValidationError):
            parent.write({"parent_id": child.id})

        self.assertFalse(parent.parent_id)

    def test_fibonacci_estimation_is_narrow_and_validated(self):
        self.project.write({"agile_estimation_method": "fibonacci"})
        task = self._create_task("Estimated", agile_story_points=5)

        self.assertEqual(task.agile_story_points, 5)
        with self.assertRaises(ValidationError):
            self._create_task("Invalid estimate", agile_story_points=4)
        self.project.write({"agile_estimation_method": "none"})
        with self.assertRaises(ValidationError):
            self._create_task("No-estimate project", agile_story_points=1)

    def test_default_type_acceptance_criteria_and_backlog_sequence_are_stored(self):
        self.project.write({"agile_default_item_type_id": self.story_type.id})

        task = self._create_task(
            "Refine acceptance criteria",
            agile_acceptance_criteria="<p>Acceptance criterion</p>",
            agile_backlog_sequence=30,
        )

        self.assertEqual(task.agile_item_type_id, self.story_type)
        self.assertEqual(task.agile_backlog_sequence, 30)
        self.assertIn("Acceptance criterion", task.agile_acceptance_criteria)

    def test_project_manager_configures_types_and_employee_creates_keyed_tasks(self):
        manager = mail_new_test_user(
            self.env, "Agile manager", groups="project.group_project_manager"
        )
        employee = mail_new_test_user(
            self.env, "Agile employee", groups="project.group_project_user"
        )

        self.item_type_model.with_user(manager).create(
            {"name": "Configured Type", "code": "configured_type"}
        )
        self.item_type_model.with_user(employee).read(["name"])
        with self.assertRaises(AccessError):
            self.item_type_model.with_user(employee).create(
                {"name": "Blocked", "code": "blocked"}
            )

        task = (
            self.env["project.task"]
            .with_user(employee)
            .create({"name": "Employee work", "project_id": self.project.id})
        )
        self.assertEqual(task.agile_key, "ENG-1")

    def test_seeded_item_types_and_stable_ui_xml_ids_are_installed(self):
        epic = self.env.ref("project_agile.project_agile_item_type_epic")
        story = self.env.ref("project_agile.project_agile_item_type_story")
        task = self.env.ref("project_agile.project_agile_item_type_task")

        self.assertEqual((epic.code, story.code, task.code), ("epic", "story", "task"))
        self.assertIn(story, epic.allowed_child_type_ids)
        self.assertIn(task, story.allowed_child_type_ids)

        for xml_id in (
            "project_agile.view_project_form_agile",
            "project_agile.view_task_form_agile",
            "project_agile.view_task_list_agile",
            "project_agile.view_task_kanban_agile",
            "project_agile.view_task_search_agile",
            "project_agile.action_project_agile_backlog",
            "project_agile.action_project_agile_item_type",
        ):
            self.assertTrue(self.env.ref(xml_id))

        backlog_action = self.env.ref("project_agile.action_project_agile_backlog")
        self.assertEqual(backlog_action.res_model, "project.task")
        self.assertIn("project_id.agile_enabled", backlog_action.domain)

    def test_backlog_ordering_respects_explicit_sequence_and_opt_in(self):
        later = self._create_task("Later backlog item", agile_backlog_sequence=30)
        earlier = self._create_task("Earlier backlog item", agile_backlog_sequence=10)
        ordinary_project = self.env["project.project"].create(
            {"name": "Ordinary", "privacy_visibility": "employees"}
        )
        ordinary = self.env["project.task"].create(
            {
                "name": "Ordinary task",
                "project_id": ordinary_project.id,
                "agile_backlog_sequence": 1,
            }
        )

        backlog = self.env["project.task"].search(
            [("project_id.agile_enabled", "=", True)],
            order="agile_backlog_sequence, id",
        )

        self.assertLess(backlog.ids.index(earlier.id), backlog.ids.index(later.id))
        self.assertNotIn(ordinary, backlog)

"""Native release navigation, scope and opt-in regression coverage."""

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install", "agile_milestones")
class TestAgileMilestones(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            "milestone_member",
            groups="project.group_project_user,project.group_project_milestone",
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Release Project",
                "agile_enabled": True,
                "agile_key": "RELEASE",
                "allow_milestones": True,
                "privacy_visibility": "employees",
            }
        )
        cls.milestone = cls.env["project.milestone"].create(
            {
                "name": "Release One",
                "project_id": cls.project.id,
            }
        )
        cls.other = cls.milestone.copy({"name": "Release Two"})
        cls.item_type = cls.env["project.agile.item.type"].create(
            {
                "name": "Release Story",
                "code": "release_story",
            }
        )
        cls.task = cls.env["project.task"].create(
            {
                "name": "Release work",
                "project_id": cls.project.id,
                "milestone_id": cls.milestone.id,
                "agile_item_type_id": cls.item_type.id,
            }
        )

    def test_contents_remain_grouped_for_one_task_and_include_done_work(self):
        milestone = self.milestone.with_user(self.user)
        action = milestone.action_view_tasks()
        self.assertEqual(action["views"][0][1], "list")
        self.assertNotIn("res_id", action)
        self.assertEqual(action["context"]["group_by"], ["agile_item_type_id", "state"])
        done = self.task.copy({"name": "Delivered", "state": "1_done"})
        foreign = self.task.copy(
            {"name": "Other release", "milestone_id": self.other.id}
        )
        tasks = self.env["project.task"].with_user(self.user).search(action["domain"])
        self.assertEqual(set(tasks.ids), {self.task.id, done.id})
        self.assertNotIn(foreign, tasks)
        groups = (
            self.env["project.task"]
            .with_user(self.user)
            ._read_group(action["domain"], ["agile_item_type_id", "state"], ["__count"])
        )
        self.assertEqual(
            {(item.id, state, count) for item, state, count in groups},
            {
                (self.item_type.id, "01_in_progress", 1),
                (self.item_type.id, "1_done", 1),
            },
        )

    def test_native_non_agile_single_task_navigation_is_unchanged(self):
        project = self.env["project.project"].create(
            {
                "name": "Native Project",
                "allow_milestones": True,
                "privacy_visibility": "employees",
            }
        )
        milestone = self.env["project.milestone"].create(
            {
                "name": "Native checkpoint",
                "project_id": project.id,
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Native work",
                "project_id": project.id,
                "milestone_id": milestone.id,
            }
        )
        action = milestone.with_user(self.user).action_view_tasks()
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["res_id"], task.id)
        self.assertNotIn("group_by", action["context"])

    def test_agile_activation_does_not_enable_milestones(self):
        project = self.env["project.project"].create({"name": "Disabled milestones"})
        self.assertFalse(project.allow_milestones)
        project.write({"agile_enabled": True, "agile_key": "NOIMPLICIT"})
        self.assertFalse(project.allow_milestones)
        self.project.allow_milestones = False
        # Disabling the last native milestone Project revokes Use Milestones.
        self.assertFalse(self.user.has_group("project.group_project_milestone"))
        with self.assertRaises(AccessError):
            self.milestone.with_user(self.user).action_view_tasks()

    def test_private_milestone_cannot_be_opened_or_found_by_name(self):
        private = self.env["project.project"].create(
            {
                "name": "Private Release",
                "agile_enabled": True,
                "agile_key": "PRIVRELEASE",
                "allow_milestones": True,
                "privacy_visibility": "followers",
            }
        )
        milestone = self.env["project.milestone"].create(
            {
                "name": "Confidential milestone",
                "project_id": private.id,
            }
        )
        with self.assertRaises(AccessError):
            milestone.with_user(self.user).action_view_tasks()
        model = self.env["project.milestone"].with_user(self.user)
        self.assertFalse(model.search([("name", "ilike", "Confidential milestone")]))
        tasks = self.env["project.task"].with_user(self.user)
        self.assertEqual(
            tasks.search([("milestone_id", "=", self.milestone.id)]),
            self.task.with_user(self.user),
        )
        self.assertEqual(
            tasks.search([("milestone_id", "ilike", "Release One")]),
            self.task.with_user(self.user),
        )

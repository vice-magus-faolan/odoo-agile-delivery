"""Current authority and native keyboard creation/navigation regressions."""

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestPlanningKeyboardCommands(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            "keyboard_planner",
            groups="project_agile.group_agile_member,project.group_project_milestone",
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Keyboard planning",
                "agile_enabled": True,
                "agile_key": "KEYBOARD",
                "allow_milestones": True,
                "privacy_visibility": "employees",
            }
        )
        cls.team = cls.env["project.agile.team"].create(
            {
                "name": "Keyboard team",
                "project_id": cls.project.id,
            }
        )
        cls.milestone = cls.env["project.milestone"].create(
            {
                "name": "Keyboard release",
                "project_id": cls.project.id,
            }
        )
        cls.item_type = cls.env["project.agile.item.type"].create(
            {
                "name": "Keyboard story",
                "code": "keyboard_story",
                "can_schedule_in_sprint": True,
            }
        )
        cls.project.agile_default_item_type_id = cls.item_type
        cls.task = cls.env["project.task"].create(
            {
                "name": "Keyboard existing work",
                "project_id": cls.project.id,
                "agile_team_id": cls.team.id,
                "milestone_id": cls.milestone.id,
            }
        )
        cls.sprint = cls.env["project.sprint"].create(
            {
                "name": "Keyboard active Sprint",
                "project_id": cls.project.id,
                "team_id": cls.team.id,
            }
        )
        cls.sprint.action_start()

    def _create(self, **kwargs):
        return (
            self.env["project.project"]
            .with_user(self.user)
            .create_agile_planning_task(
                self.project.id, "Keyboard created work", team_id=self.team.id, **kwargs
            )
        )

    def test_quick_create_uses_native_defaults_and_ignores_context_injection(self):
        task_id = (
            self.env["project.project"]
            .with_user(self.user)
            .with_context(
                default_agile_key="FORGED-1",
                default_parent_id=self.task.id,
                default_sprint_id=self.sprint.id,
                default_agile_story_points=-4,
            )
            .create_agile_planning_task(
                self.project.id,
                "Keyboard created work",
                team_id=self.team.id,
                milestone_id=self.milestone.id,
            )
        )
        task = self.env["project.task"].browse(task_id)
        self.assertEqual(task.project_id, self.project)
        self.assertEqual(task.agile_item_type_id, self.item_type)
        self.assertEqual(task.agile_team_id, self.team)
        self.assertEqual(task.milestone_id, self.milestone)
        self.assertTrue(task.agile_key.startswith("KEYBOARD-"))
        self.assertNotEqual(task.agile_key, self.task.agile_key)
        self.assertFalse(task.sprint_id)
        self.assertFalse(task.parent_id)
        self.assertEqual(task.agile_story_points, 0)
        self.assertEqual(task.stage_id, task._first_agile_stage())
        self.assertIn(
            task_id,
            [
                row["id"]
                for row in self.project.with_user(
                    self.user
                ).get_agile_planning_snapshot(self.project.id, team_id=self.team.id)[
                    "backlog"
                ]["items"]
            ],
        )

    def test_stale_project_and_archived_team_cannot_create(self):
        count = (
            self.env["project.task"]
            .with_context(active_test=False)
            .search_count([("project_id", "=", self.project.id)])
        )
        self.team.active = False
        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(self.user).with_context(
                active_test=False
            ).create_agile_planning_task(
                self.project.id, "Rejected", team_id=self.team.id
            )
        self.team.active = True
        self.project.active = False
        with self.assertRaises(AccessError):
            self._create()
        with self.assertRaises(ValidationError):
            self.project.with_user(
                self.user
            ).action_open_agile_planning_active_sprints()
        self.assertEqual(
            self.env["project.task"]
            .with_context(active_test=False)
            .search_count([("project_id", "=", self.project.id)]),
            count,
        )

    def test_current_scope_is_checked_after_archival_or_access_revocation(self):
        project = self.env["project.project"].create(
            {
                "name": "Private keyboard work",
                "privacy_visibility": "followers",
                "agile_enabled": True,
                "agile_key": "PRIVATEKEY",
            }
        )
        # Archival invalidates a previously visible autocomplete selection.
        self.task.active = False
        with self.assertRaises(AccessError):
            self.project.with_user(self.user).action_open_agile_planning_task(
                self.task.id
            )
        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(self.user).create_agile_planning_task(
                project.id, "No hidden work"
            )
        self.task.active = True
        self.project.privacy_visibility = "followers"
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.project.with_user(self.user).action_open_agile_planning_task(
                self.task.id
            )
        with self.assertRaises(AccessError):
            self._create()
        self.project.privacy_visibility = "employees"
        self.env.invalidate_all()
        self.assertEqual(
            self.project.with_user(self.user).action_open_agile_planning_backlog()[
                "res_model"
            ],
            "project.task",
        )

    def test_commands_keep_current_team_scope_and_use_native_key_search(self):
        action = self.project.with_user(
            self.user
        ).action_open_agile_planning_active_sprints(team_id=self.team.id)
        self.assertEqual(
            self.env["project.sprint"].with_user(self.user).search(action["domain"]),
            self.sprint,
        )
        matches = (
            self.env["project.task"]
            .with_user(self.user)
            .name_search(
                self.task.agile_key.lower(),
                domain=[("project_id", "=", self.project.id)],
            )
        )
        self.assertEqual(matches[0][0], self.task.id)
        self.assertEqual(
            self.project.with_user(self.user).action_open_agile_planning_task(
                matches[0][0]
            )["res_id"],
            self.task.id,
        )
        with self.assertRaises(ValidationError):
            self.env["project.project"].with_user(self.user).create_agile_planning_task(
                self.project.id, " "
            )

    def test_native_keyboard_create_cancel_filters_and_find(self):
        self.assertFalse(self.user.has_group("base.group_system"))
        self.assertFalse(self.user.has_group("project.group_project_manager"))
        action = self.env["ir.actions.client"].create(
            {
                "name": "Keyboard planning",
                "tag": "project_agile_ui.planning",
                "context": repr({"project_id": self.project.id}),
            }
        )
        before = self.env["project.task"].search_count(
            [("project_id", "=", self.project.id)]
        )
        self.start_tour(
            f"/odoo/action-{action.id}",
            "agile_planning_keyboard",
            login=self.user.login,
        )
        for command in ("active", "backlog"):
            self.start_tour(
                f"/odoo/action-{action.id}",
                f"agile_keyboard_{command}",
                login=self.user.login,
            )
        tasks = self.env["project.task"].search([("project_id", "=", self.project.id)])
        self.assertEqual(len(tasks), before + 1)
        self.assertFalse(
            tasks.filtered(lambda task: task.name == "Keyboard canceled work")
        )
        task = tasks.filtered(lambda task: task.name == "Keyboard saved work")
        self.assertEqual(len(task), 1)
        self.assertEqual(task.agile_team_id, self.team)
        self.assertEqual(task.agile_item_type_id, self.item_type)
        self.assertEqual(task.milestone_id, self.milestone)
        self.assertTrue(task.agile_key.startswith("KEYBOARD-"))
        self.assertFalse(task.sprint_id)

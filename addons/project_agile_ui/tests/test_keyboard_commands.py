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

        cls.foreign_project = cls.env["project.project"].create(
            {
                "name": "Other readable keyboard planning",
                "company_id": cls.project.company_id.id,
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "OTHERKEY",
                "allow_milestones": True,
                "agile_default_item_type_id": cls.item_type.id,
            }
        )
        cls.foreign_team = cls.env["project.agile.team"].create(
            {"name": "Other readable team", "project_id": cls.foreign_project.id}
        )
        cls.foreign_milestone = cls.env["project.milestone"].create(
            {"name": "Other readable release", "project_id": cls.foreign_project.id}
        )
        cls.foreign_task = cls.env["project.task"].create(
            {
                "name": "Other readable work",
                "project_id": cls.foreign_project.id,
                "agile_team_id": cls.foreign_team.id,
                "milestone_id": cls.foreign_milestone.id,
            }
        )

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

    def test_quick_create_rejects_readable_team_from_another_project(self):
        projects = self.env["project.project"].with_user(self.user)
        team = self.foreign_team.with_user(self.user)
        self.assertFalse(projects.env.su)
        self.assertEqual(self.foreign_project.company_id, self.project.company_id)
        self.assertEqual(team.company_id, self.project.company_id)
        self.assertEqual(
            projects.search([("id", "in", (self.project | self.foreign_project).ids)]),
            self.project | self.foreign_project,
        )
        self.assertEqual(team.search([("id", "=", team.id)]), team)
        self.assertEqual(team.read(["name"])[0]["name"], "Other readable team")
        tasks = self.env["project.task"].with_context(active_test=False)
        before = tasks.search([])
        with self.assertRaises(AccessError) as rejected, self.cr.savepoint():
            projects.create_agile_planning_task(
                self.project.id, "Rejected foreign team", team_id=team.id
            )
        self.assertEqual(
            str(rejected.exception), "The Agile planning team is unavailable."
        )
        self.assertEqual(tasks.search([]), before)
        created_id = projects.create_agile_planning_task(
            self.foreign_project.id, "Valid foreign team", team_id=team.id
        )
        created = tasks.browse(created_id)
        self.assertEqual(created.project_id, self.foreign_project)
        self.assertEqual(created.agile_team_id, self.foreign_team)
        self.assertEqual(tasks.search([]), before | created)

    def test_quick_create_rejects_readable_milestone_from_another_project(self):
        projects = self.env["project.project"].with_user(self.user)
        milestone = self.foreign_milestone.with_user(self.user)
        self.assertFalse(projects.env.su)
        self.assertEqual(self.foreign_project.company_id, self.project.company_id)
        self.assertTrue(self.project.allow_milestones)
        self.assertTrue(self.user.has_group("project.group_project_milestone"))
        self.assertEqual(
            projects.search([("id", "in", (self.project | self.foreign_project).ids)]),
            self.project | self.foreign_project,
        )
        self.assertEqual(milestone.search([("id", "=", milestone.id)]), milestone)
        self.assertEqual(milestone.read(["name"])[0]["name"], "Other readable release")
        tasks = self.env["project.task"].with_context(active_test=False)
        before = tasks.search([])
        with self.assertRaises(AccessError) as rejected, self.cr.savepoint():
            projects.create_agile_planning_task(
                self.project.id,
                "Rejected foreign milestone",
                team_id=self.team.id,
                milestone_id=milestone.id,
            )
        self.assertEqual(
            str(rejected.exception), "The planning milestone is unavailable."
        )
        self.assertEqual(tasks.search([]), before)
        created_id = projects.create_agile_planning_task(
            self.foreign_project.id,
            "Valid foreign milestone",
            team_id=self.foreign_team.id,
            milestone_id=milestone.id,
        )
        created = tasks.browse(created_id)
        self.assertEqual(created.project_id, self.foreign_project)
        self.assertEqual(created.milestone_id, self.foreign_milestone)
        self.assertEqual(tasks.search([]), before | created)

    def test_quick_create_honors_task_create_rule_for_project_reader(self):
        projects = self.env["project.project"].with_user(self.user)
        tasks = self.env["project.task"].with_context(active_test=False)
        self.assertFalse(projects.env.su)
        self.assertFalse(self.user.has_group("base.group_system"))
        self.assertFalse(self.user.has_group("project.group_project_manager"))
        rule = self.env["ir.rule"].create(
            {
                "name": "Deny keyboard Task creation only",
                "model_id": self.env["ir.model"]._get_id("project.task"),
                "domain_force": repr([("project_id", "!=", self.project.id)]),
                "perm_read": False,
                "perm_create": True,
                "perm_write": False,
                "perm_unlink": False,
                "active": False,
            }
        )
        before = tasks.search([])
        allowed = tasks.browse(self._create())
        self.assertEqual(allowed.project_id, self.project)
        self.assertEqual(allowed.agile_team_id, self.team)
        self.assertTrue(allowed.agile_key.startswith("KEYBOARD-"))
        self.assertEqual(tasks.search([]), before | allowed)
        rule.active = True
        self.env.invalidate_all()
        self.assertEqual(projects.search([("id", "=", self.project.id)]), self.project)
        self.assertEqual(
            self.task.with_user(self.user).read(["name"])[0]["name"], self.task.name
        )
        # Model create access remains; the native rule must reject the new row.
        tasks.with_user(self.user).check_access("create")
        with self.assertRaises(AccessError), self.cr.savepoint():
            self._create()
        self.assertEqual(tasks.search([]), before | allowed)
        rule.active = False
        self.env.invalidate_all()
        restored = tasks.browse(self._create())
        self.assertEqual(restored.project_id, self.project)
        self.assertEqual(restored.agile_team_id, self.team)
        self.assertNotEqual(restored.agile_key, allowed.agile_key)
        self.assertEqual(tasks.search([]), before | allowed | restored)

    def test_task_open_rejects_readable_task_from_another_project(self):
        projects = self.env["project.project"].with_user(self.user)
        task = self.foreign_task.with_user(self.user)
        self.assertFalse(projects.env.su)
        self.assertEqual(self.foreign_project.company_id, self.project.company_id)
        self.assertEqual(
            projects.search([("id", "in", (self.project | self.foreign_project).ids)]),
            self.project | self.foreign_project,
        )
        self.assertEqual(task.search([("id", "=", task.id)]), task)
        self.assertEqual(task.read(["name"])[0]["name"], "Other readable work")
        tasks = self.env["project.task"].with_context(active_test=False)
        before = tasks.search([])
        fields = ["name", "project_id", "agile_key", "agile_team_id", "milestone_id"]
        history = (self.task | self.foreign_task).read(fields, load=None)
        with self.assertRaises(AccessError) as rejected, self.cr.savepoint():
            self.project.with_user(self.user).action_open_agile_planning_task(task.id)
        self.assertEqual(str(rejected.exception), "The work item is unavailable.")
        for project, selected in (
            (self.project, self.task),
            (self.foreign_project, self.foreign_task),
        ):
            self.assertEqual(
                project.with_user(self.user).action_open_agile_planning_task(
                    selected.id
                ),
                {
                    "type": "ir.actions.act_window",
                    "res_model": "project.task",
                    "res_id": selected.id,
                    "views": [(False, "form")],
                    "target": "current",
                },
            )
        self.assertEqual(tasks.search([]), before)
        self.assertEqual(
            (self.task | self.foreign_task).read(fields, load=None), history
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

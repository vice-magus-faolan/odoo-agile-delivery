from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestAgileRoleAssignmentTour(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.editor = mail_new_test_user(
            cls.env, "agile_settings_editor", groups="base.group_system"
        )
        cls.approver = mail_new_test_user(
            cls.env, "agile_widget_approver", groups="project.group_project_manager"
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Native assigned role capabilities",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "WIDGET",
            }
        )

    def _target(self, name, manager=False):
        user = mail_new_test_user(
            self.env,
            "agile_widget_" + name,
            groups="project.group_project_manager"
            if manager
            else "project.group_project_user",
        )
        self.assertEqual(user.has_group("project.group_project_manager"), manager)
        self.assertFalse(user.has_group("base.group_system"))
        return user

    def _tour(self, user, name):
        action = self.env.ref("base.action_res_users")
        self.start_tour(
            f"/odoo/action-{action.id}/{user.id}", name, login=self.editor.login
        )
        # HTTP saves invalidate another environment; read the persisted target.
        self.env.invalidate_all()

    def _assert_roles(self, user, analyst, master, manager=False):
        self.assertEqual(
            user.has_group("project_agile_solution.group_business_analyst"), analyst
        )
        self.assertEqual(user.has_group("project_scrum.group_scrum_master"), master)
        self.assertEqual(user.has_group("project.group_project_manager"), manager)
        self.assertTrue(user.has_group("project_agile.group_agile_member"))
        self.assertTrue(user.has_group("project.group_project_user"))
        self.assertFalse(user.has_group("base.group_system"))

    def _assert_capabilities(self, user, analyst, master, manager):
        solutions = self.env["project.agile.solution"].with_user(user)
        values = {"name": "Assigned author", "project_id": self.project.id}
        if analyst or manager:
            solution = solutions.create(values)
            self.env["project.agile.requirement"].with_user(user).create(
                {"name": "Assigned requirement", "solution_id": solution.id}
            )
            document = (
                self.env["project.agile.solution.document"]
                .with_user(user)
                .create(
                    {
                        "name": "Assigned document",
                        "solution_id": solution.id,
                        "approver_id": self.approver.id,
                    }
                )
            )
            action = document.action_new_revision()
            revision = (
                self.env[action["res_model"]].with_user(user).browse(action["res_id"])
            )
            revision.action_submit()
            if not manager:
                with self.assertRaises(AccessError):
                    revision.action_approve()
        else:
            with self.assertRaises(AccessError):
                solutions.create(values)
        teams = self.env["project.agile.team"].with_user(user)
        team_values = {"name": "Assigned operator", "project_id": self.project.id}
        if master or manager:
            team = teams.create(team_values)
            sprint = (
                self.env["project.sprint"]
                .with_user(user)
                .create(
                    {
                        "name": "Assigned Sprint",
                        "project_id": self.project.id,
                        "team_id": team.id,
                    }
                )
            )
            sprint.action_start()
            sprint.action_close()
            self.assertEqual(sprint.state, "closed")
        else:
            with self.assertRaises(AccessError):
                teams.create(team_values)
        if not manager:
            with self.assertRaises(AccessError):
                self.project.with_user(user).write({"agile_enabled": False})

    def test_existing_combined_roles_survive_native_privilege_edit(self):
        # Reproduce the old widget losing one ORM-assigned sibling on any edit.
        user = self._target("existing_combined")
        user.write(
            {
                "group_ids": [
                    Command.link(
                        self.env.ref("project_agile_solution.group_business_analyst").id
                    ),
                    Command.link(self.env.ref("project_scrum.group_scrum_master").id),
                ]
            }
        )
        self._assert_roles(user, True, True)
        self._tour(user, "agile_edit_export_privilege")
        self._assert_roles(user, True, True)
        self.assertTrue(user.has_group("base.group_allow_export"))

    def test_native_assignment_save_reload_edit_preserves_roles_and_authority(self):
        cases = (
            ("analyst", True, False),
            ("master", False, True),
            ("combined", True, True),
        )
        for manager in (False, True):
            for name, analyst, master in cases:
                with self.subTest(role=name, manager=manager):
                    user = self._target(name + ("_manager" if manager else ""), manager)
                    self._tour(user, "agile_assign_" + name)
                    self._assert_roles(user, analyst, master, manager)
                    # start_tour opens a fresh browser on the saved existing user.
                    self._tour(user, "agile_edit_export_privilege")
                    self._assert_roles(user, analyst, master, manager)
                    self.assertTrue(user.has_group("base.group_allow_export"))
                    self._assert_capabilities(user, analyst, master, manager)

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestScrumRoles(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.master = mail_new_test_user(
            cls.env,
            "role_scrum_master",
            groups="project_scrum.group_scrum_master",
            company_id=cls.env.company.id,
            company_ids=[Command.set(cls.env.company.ids)],
        )
        cls.member = mail_new_test_user(
            cls.env, "role_scrum_member", groups="project_agile.group_agile_member"
        )
        cls.other_company = cls.env["res.company"].create({"name": "Other roles"})
        cls.project = cls.env["project.project"].create(
            {
                "name": "Scrum roles",
                "agile_enabled": True,
                "agile_key": "SMROLE",
                "privacy_visibility": "employees",
                "company_id": cls.env.company.id,
            }
        )
        cls.hidden = cls.env["project.project"].create(
            {
                "name": "Private roles",
                "agile_enabled": True,
                "agile_key": "SMHIDE",
                "privacy_visibility": "followers",
                "company_id": cls.env.company.id,
            }
        )
        cls.foreign = cls.env["project.project"].create(
            {
                "name": "Foreign roles",
                "agile_enabled": True,
                "agile_key": "SMOTHER",
                "privacy_visibility": "employees",
                "company_id": cls.other_company.id,
            }
        )

    def _team(self, project, user=None):
        return (
            self.env["project.agile.team"]
            .with_user(user or self.env.user)
            .create(
                {
                    "name": "Role team",
                    "project_id": project.id,
                }
            )
        )

    def _sprint(self, team, user=None):
        return (
            self.env["project.sprint"]
            .with_user(user or self.env.user)
            .create(
                {
                    "name": "Role Sprint",
                    "project_id": team.project_id.id,
                    "team_id": team.id,
                }
            )
        )

    def test_master_runs_sprint_member_places_work_without_administration(self):
        for user in (self.master, self.member):
            self.assertFalse(user.has_group("project.group_project_manager"))
        team = self._team(self.project, self.master)
        team.write({"name": "Maintained by Scrum master"})
        sprint = self._sprint(team, self.master)
        task = (
            self.env["project.task"]
            .with_user(self.member)
            .create(
                {
                    "name": "Member work",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.env.ref(
                        "project_agile.project_agile_item_type_story"
                    ).id,
                }
            )
        )
        action = task.action_assign_to_sprint()
        self.env[action["res_model"]].with_user(self.member).with_context(
            **action["context"]
        ).create({"sprint_id": sprint.id}).action_confirm()
        self.assertEqual(task.sprint_id, sprint)
        sprint.action_start()
        self.assertEqual(sprint.state, "active")
        action = sprint.action_close()
        self.env[action["res_model"]].with_user(self.master).with_context(
            **action["context"]
        ).create({"unfinished_disposition": "product_backlog"}).action_confirm()
        self.assertEqual(sprint.state, "closed")
        self.assertFalse(task.sprint_id)
        with self.assertRaises(AccessError):
            self._team(self.project, self.member)
        with self.assertRaises(AccessError):
            self._sprint(team, self.member)
        with self.assertRaises(AccessError):
            self.project.with_user(self.master).write({"agile_enabled": False})
        for action in (
            sprint.with_user(self.member).action_start,
            sprint.with_user(self.member).action_close,
        ):
            with self.assertRaises(AccessError):
                action()

    def test_team_menu_is_reachable_under_tasks_for_scrum_master(self):
        team_menu = self.env.ref("project_scrum.menu_project_agile_team")
        sprint_menu = self.env.ref("project_scrum.menu_project_sprint")
        tasks_menu = self.env.ref("project.menu_project_management")
        self.assertEqual(team_menu.parent_id, tasks_menu)
        self.assertEqual(sprint_menu.parent_id, tasks_menu)
        self.assertEqual(team_menu.action.res_model, "project.agile.team")
        self.assertFalse(team_menu.child_id)
        visible = self.env["ir.ui.menu"].with_user(self.master)._visible_menu_ids()
        self.assertTrue({team_menu.id, sprint_menu.id, tasks_menu.id} <= visible)
        self.assertNotIn(
            team_menu.id,
            self.env["ir.ui.menu"].with_user(self.member)._visible_menu_ids(),
        )
        team = self._team(self.project, self.master)
        self.assertIn(
            team,
            self.env[team_menu.action.res_model].with_user(self.master).search([]),
        )

    def test_master_private_company_and_current_project_access_are_not_implied(self):
        self.assertFalse(self.master.has_group("project.group_project_manager"))
        for project in (self.hidden, self.foreign):
            team = self._team(project)
            sprint = self._sprint(team)
            caller = sprint.with_user(self.master)
            self.assertFalse(caller.search([("id", "=", sprint.id)]))
            for action in (
                lambda project=project: self._team(project, self.master),
                lambda team=team: self._sprint(team, self.master),
                caller.action_start,
                lambda caller=caller: caller.write({"goal": "Forbidden"}),
                lambda team=team: team.with_user(self.master).write(
                    {"name": "Forbidden"}
                ),
            ):
                with self.assertRaises(AccessError), self.cr.savepoint():
                    action()
            sprint.action_start()
            with self.assertRaises(AccessError):
                caller.action_close()
        with self.assertRaises(AccessError):
            self.env["project.agile.team"].with_user(self.master).with_context(
                allowed_company_ids=self.other_company.ids, sudo=True
            ).create({"name": "Forged company", "project_id": self.foreign.id})
        team = self._team(self.project, self.master)
        sprint = self._sprint(team, self.master)
        self.env["ir.rule"].create(
            {
                "name": "Revoke native Project",
                "model_id": self.env.ref("project.model_project_project").id,
                "domain_force": repr([("id", "!=", self.project.id)]),
            }
        )
        with self.assertRaises(AccessError):
            sprint.action_start()
        with self.assertRaises(AccessError):
            team.write({"name": "Revoked"})
        self.assertEqual(sprint.state, "draft")

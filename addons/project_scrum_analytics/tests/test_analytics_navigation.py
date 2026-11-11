from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestAnalyticsNavigation(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            "analytics_navigation_user",
            groups="project.group_project_user",
            company_id=cls.env.company.id,
            company_ids=[Command.set(cls.env.company.ids)],
        )
        cls.employee = mail_new_test_user(
            cls.env, "analytics_navigation_employee", groups="base.group_user"
        )
        other_company = cls.env["res.company"].create(
            {"name": "Analytics navigation other company"}
        )
        cls.sprints = cls.env["project.sprint"]
        for name, key, privacy, company in (
            ("Visible navigation", "NAVVISIBLE", "followers", cls.env.company),
            ("Private navigation", "NAVPRIVATE", "followers", cls.env.company),
            ("Other company navigation", "NAVOTHER", "employees", other_company),
        ):
            project = cls.env["project.project"].create(
                {
                    "name": name,
                    "agile_key": key,
                    "agile_enabled": True,
                    "agile_estimation_method": "fibonacci",
                    "privacy_visibility": privacy,
                    "company_id": company.id,
                }
            )
            team = cls.env["project.agile.team"].create(
                {"name": name, "project_id": project.id}
            )
            task = cls.env["project.task"].create(
                {
                    "name": name,
                    "project_id": project.id,
                    "agile_item_type_id": cls.env.ref(
                        "project_agile.project_agile_item_type_story"
                    ).id,
                    "agile_story_points": 5,
                }
            )
            sprint = cls.env["project.sprint"].create(
                {
                    "name": name,
                    "project_id": project.id,
                    "team_id": team.id,
                    "task_ids": [Command.set(task.ids)],
                }
            )
            sprint.action_start()
            cls.sprints |= sprint
        cls.visible = cls.sprints[0]
        cls.visible.project_id.message_subscribe(partner_ids=cls.user.partner_id.ids)

    def test_menu_role_and_projection_access(self):
        self.assertFalse(self.user.has_group("project.group_project_manager"))
        self.assertFalse(self.employee.has_group("project.group_project_user"))
        menus = self.env["ir.ui.menu"].with_user(self.employee).load_menus(False)
        for xmlid in (
            "menu_scrum_analytics",
            "menu_scrum_analytics_report",
            "menu_scrum_analytics_timeline",
        ):
            self.assertNotIn(self.env.ref(f"project_scrum_analytics.{xmlid}").id, menus)
        for model in (
            "project.scrum.analytics.report",
            "project.scrum.analytics.timeline",
        ):
            records = (
                self.env[model]
                .with_user(self.user)
                .with_context(allowed_company_ids=self.user.company_ids.ids)
            )
            domain = [("sprint_id", "in", self.sprints.ids)]
            visible = records.search(domain)
            self.assertTrue(visible)
            self.assertEqual(visible.sprint_id.ids, self.visible.ids)
            for hidden in self.sprints[1:]:
                restricted = self.env[model].search([("sprint_id", "=", hidden.id)])
                self.assertTrue(restricted)
                with self.assertRaises(AccessError):
                    restricted.with_user(self.user).check_access("read")
            with self.assertRaises(AccessError):
                self.env[model].with_user(self.employee).search(domain)
            with self.assertRaises(AccessError):
                visible.write({"burnup_total": 99})
            with self.assertRaises(AccessError):
                records.create({})
            with self.assertRaises(AccessError):
                visible.unlink()

    def test_project_user_opens_both_report_leaves(self):
        events = self.sprints.scope_event_ids
        before = events.read(
            ["sprint_id", "task_id", "event_type", "event_at", "story_points"]
        )
        self.start_tour("/odoo", "scrum_analytics_navigation", login=self.user.login)
        events.invalidate_recordset()
        self.assertEqual(
            events.read(
                ["sprint_id", "task_id", "event_type", "event_at", "story_points"]
            ),
            before,
        )
        self.assertEqual(self.sprints.scope_event_ids, events)

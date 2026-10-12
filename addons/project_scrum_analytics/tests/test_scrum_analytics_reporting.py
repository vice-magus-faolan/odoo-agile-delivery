from datetime import timedelta

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestScrumAnalyticsReporting(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Reporting Project",
                "privacy_visibility": "followers",
                "agile_enabled": True,
                "agile_key": "REPORTING",
                "agile_estimation_method": "fibonacci",
            }
        )
        self.team = self.env["project.agile.team"].create(
            {"name": "Reporting Team", "project_id": self.project.id}
        )
        self.item_type = self.env["project.agile.item.type"].create(
            {
                "name": "Reporting Story",
                "code": "reporting_story",
                "can_schedule_in_sprint": True,
            }
        )
        self.task = self.env["project.task"].create(
            {
                "name": "Reporting task",
                "project_id": self.project.id,
                "agile_item_type_id": self.item_type.id,
                "agile_story_points": 5,
            }
        )

    def _create_sprint(self, project=None, team=None, task_ids=None):
        return self.env["project.sprint"].create(
            {
                "name": "Reporting Sprint",
                "project_id": (project or self.project).id,
                "team_id": (team or self.team).id,
                "task_ids": task_ids or [],
            }
        )

    def test_report_records_and_timeline_expose_all_accepted_metrics(self):
        sprint = self._create_sprint(task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        self.task.write({"state": "1_done"})

        report = self.env["project.scrum.analytics.report"].search(
            [("sprint_id", "=", sprint.id)]
        )
        timeline = self.env["project.scrum.analytics.timeline"].search(
            [("report_id", "=", report.id)]
        )

        self.assertEqual(len(report), 1)
        self.assertEqual(report.state, "active")
        self.assertEqual(report.velocity, 0.0)
        self.assertEqual(report.burndown_remaining, 0.0)
        self.assertEqual(report.burnup_completed, 5.0)
        self.assertEqual(report.burnup_total, 5.0)
        self.assertEqual(report.scope_initial, 5.0)
        self.assertEqual(report.scope_final, 5.0)
        self.assertEqual(report.commitment_points, 5.0)
        self.assertEqual(report.completed_commitment_points, 5.0)
        self.assertEqual(report.commitment_completion_ratio, 1.0)
        self.assertEqual(report.points_unit, "story_points")
        self.assertEqual(report.completion_ratio_unit, "fraction")
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[-1].burndown_remaining, 0.0)
        self.assertEqual(timeline[-1].burnup_completed, 5.0)
        self.assertEqual(timeline[-1].burnup_total, 5.0)

        sprint.action_close()

        self.assertEqual(report.velocity, 5.0)
        self.assertEqual(report.precision, "trusted")
        self.assertTrue(report.closed_at)

    def test_actions_and_views_are_additive_and_drill_down_only_to_authorized_records(
        self,
    ):
        sprint = self._create_sprint(task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        report = self.env["project.scrum.analytics.report"].search(
            [("sprint_id", "=", sprint.id)]
        )
        timeline = self.env["project.scrum.analytics.timeline"].search(
            [("report_id", "=", report.id)]
        )

        report_action = self.env.ref(
            "project_scrum_analytics.action_scrum_analytics_report"
        )
        timeline_action = self.env.ref(
            "project_scrum_analytics.action_scrum_analytics_timeline"
        )
        self.assertEqual(report_action.res_model, "project.scrum.analytics.report")
        self.assertEqual(timeline_action.res_model, "project.scrum.analytics.timeline")
        self.assertEqual(
            self.env.ref(
                "project_scrum_analytics.view_scrum_analytics_report_pivot"
            ).type,
            "pivot",
        )
        self.assertEqual(
            self.env.ref(
                "project_scrum_analytics.view_scrum_analytics_report_graph"
            ).type,
            "graph",
        )
        self.assertEqual(
            self.env.ref(
                "project_scrum_analytics.view_scrum_analytics_timeline_pivot"
            ).type,
            "pivot",
        )
        self.assertEqual(
            self.env.ref(
                "project_scrum_analytics.view_scrum_analytics_timeline_graph"
            ).type,
            "graph",
        )
        self.assertEqual(
            report.action_open_timeline()["domain"], [("report_id", "=", report.id)]
        )
        self.assertEqual(report.action_open_sprint()["res_id"], sprint.id)
        self.assertEqual(timeline[-1].action_open_task()["res_id"], self.task.id)

    # Preserve the existing native test identifier.
    def test_report_search_grouping_export_and_drill_down_enforce_project_and_company_access(  # noqa: E501
        self,
    ):
        user = mail_new_test_user(
            self.env, "Analytics reporting user", groups="project.group_project_user"
        )
        self.project.message_subscribe(partner_ids=[user.partner_id.id])
        sprint = self._create_sprint(task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        report = self.env["project.scrum.analytics.report"].search(
            [("sprint_id", "=", sprint.id)]
        )

        foreign_project = self.env["project.project"].create(
            {
                "name": "Foreign reporting project",
                "privacy_visibility": "followers",
                "agile_enabled": True,
                "agile_key": "FOREIGNREPORT",
            }
        )
        foreign_team = self.env["project.agile.team"].create(
            {"name": "Foreign reporting team", "project_id": foreign_project.id}
        )
        foreign_sprint = self._create_sprint(project=foreign_project, team=foreign_team)
        foreign_sprint.action_start()
        foreign_report = self.env["project.scrum.analytics.report"].search(
            [("sprint_id", "=", foreign_sprint.id)]
        )

        other_company = self.env["res.company"].create(
            {"name": "Other reporting company"}
        )
        other_project = self.env["project.project"].create(
            {
                "name": "Other-company reporting project",
                "privacy_visibility": "employees",
                "company_id": other_company.id,
                "agile_enabled": True,
                "agile_key": "OTHERREPORT",
            }
        )
        other_team = self.env["project.agile.team"].create(
            {"name": "Other reporting team", "project_id": other_project.id}
        )
        other_sprint = self._create_sprint(project=other_project, team=other_team)
        other_sprint.action_start()

        reports = self.env["project.scrum.analytics.report"].with_user(user)
        timelines = self.env["project.scrum.analytics.timeline"].with_user(user)
        visible = reports.search([])

        self.assertEqual(visible, report.with_user(user))
        self.assertEqual(
            reports.search_read([], ["sprint_id", "project_id"]),
            [
                {
                    "id": report.id,
                    "sprint_id": (sprint.id, sprint.display_name),
                    "project_id": (self.project.id, self.project.display_name),
                }
            ],
        )
        self.assertEqual(
            reports.search_count([("sprint_id", "=", foreign_sprint.id)]), 0
        )
        self.assertEqual(reports.search_count([("sprint_id", "=", other_sprint.id)]), 0)
        self.assertEqual(
            timelines.search_count([("report_id", "=", foreign_report.id)]), 0
        )
        self.assertEqual(
            reports._read_group([], ["project_id"], ["__count"])[0][0], self.project
        )
        with self.assertRaises(AccessError):
            reports.browse(foreign_report.id).action_open_timeline()
        with self.assertRaises(AccessError):
            reports.browse(foreign_report.id).action_open_sprint()

    def test_superuser_close_time_recovery_resynchronizes_projections(self):
        sprint = self._create_sprint(task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        self.task.write({"state": "1_done"})
        sprint.action_close()
        report = self.env["project.scrum.analytics.report"].search(
            [("sprint_id", "=", sprint.id)]
        )

        self.assertEqual(report.burnup_completed, 5.0)
        self.assertEqual(
            self.env["project.scrum.analytics.timeline"].search_count(
                [("report_id", "=", report.id)]
            ),
            2,
        )

        sprint.sudo().write({"closed_at": sprint.closed_at - timedelta(days=1)})

        report.invalidate_recordset(
            ["burndown_remaining", "burnup_completed", "burnup_total"]
        )
        self.assertEqual(report.burndown_remaining, 0.0)
        self.assertEqual(report.burnup_completed, 0.0)
        self.assertEqual(report.burnup_total, 0.0)
        self.assertEqual(
            self.env["project.scrum.analytics.timeline"].search_count(
                [("report_id", "=", report.id)]
            ),
            0,
        )

    def test_superuser_state_write_cannot_bypass_the_lifecycle(self):
        sprint = self._create_sprint(task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        report = self.env["project.scrum.analytics.report"].search(
            [("sprint_id", "=", sprint.id)]
        )

        with self.assertRaises(ValidationError):
            sprint.sudo().write({"state": "closed"})

        self.assertEqual(sprint.state, "active")
        self.assertEqual(report.state, "active")
        self.assertFalse(sprint.closed_at)

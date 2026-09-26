from odoo import Command, fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestScrumAnalytics(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Analytics Project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "ANALYTICS",
                "agile_estimation_method": "fibonacci",
            }
        )
        self.team = self.env["project.agile.team"].create(
            {"name": "Analytics Team", "project_id": self.project.id}
        )
        self.item_type = self.env["project.agile.item.type"].create(
            {
                "name": "Analytics Story",
                "code": "analytics_story",
                "can_schedule_in_sprint": True,
            }
        )
        self.task = self.env["project.task"].create(
            {
                "name": "Committed work",
                "project_id": self.project.id,
                "agile_item_type_id": self.item_type.id,
                "agile_story_points": 5,
            }
        )

    def _create_sprint(self, task_ids=None):
        return self.env["project.sprint"].create(
            {
                "name": "Analytics Sprint",
                "project_id": self.project.id,
                "team_id": self.team.id,
                "task_ids": task_ids or [],
            }
        )

    def test_active_sprint_report_replays_initial_commitment(self):
        sprint = self._create_sprint([Command.set(self.task.ids)])
        sprint.action_start()

        report = self.env["project.scrum.analytics"].get_report(sprint.id)

        self.assertEqual(report["burndown"]["remaining"], 5.0)
        self.assertEqual(report["burnup"], {"completed": 0.0, "total": 5.0})
        self.assertEqual(
            report["scope_change"],
            {"initial": 5.0, "added": 0.0, "removed": 0.0, "final": 5.0},
        )
        self.assertEqual(
            report["commitment_completion"],
            {"commitment": 5.0, "completed": 0.0, "completion_ratio": 0.0},
        )
        self.assertEqual(report["velocity"], 0.0)

    def test_report_replays_scope_completion_reopening_and_reestimation(self):
        sprint = self._create_sprint([Command.set(self.task.ids)])
        sprint.action_start()
        self.task.write({"state": "1_done"})
        self.task.write({"state": "01_in_progress"})
        self.task.write({"state": "1_done"})
        added = self.env["project.task"].create(
            {
                "name": "Added then removed",
                "project_id": self.project.id,
                "agile_item_type_id": self.item_type.id,
                "agile_story_points": 3,
                "sprint_id": sprint.id,
            }
        )
        added.write({"agile_story_points": 5})
        added.write({"sprint_id": False})

        report = self.env["project.scrum.analytics"].get_report(sprint.id)

        self.assertEqual(report["burndown"]["remaining"], 0.0)
        self.assertEqual(report["burnup"], {"completed": 5.0, "total": 5.0})
        self.assertEqual(
            report["scope_change"],
            {"initial": 5.0, "added": 3.0, "removed": 5.0, "final": 5.0},
        )
        self.assertEqual(report["commitment_completion"]["completion_ratio"], 1.0)
        self.assertEqual(len(report["timeline"]), 7)

    def test_closed_report_is_frozen_after_later_task_edits(self):
        sprint = self._create_sprint([Command.set(self.task.ids)])
        sprint.action_start()
        self.task.write({"state": "1_done"})
        sprint.action_close()
        expected = self.env["project.scrum.analytics"].get_report(sprint.id)

        self.task.write({"state": "01_in_progress", "agile_story_points": 13})
        self.project.write({"name": "Renamed after close"})

        self.assertEqual(self.env["project.scrum.analytics"].get_report(sprint.id), expected)
        self.assertEqual(expected["velocity"], 5.0)

    def test_carry_over_and_zero_point_work_do_not_create_velocity(self):
        carry_task = self.env["project.task"].create(
            {
                "name": "Carry-over work",
                "project_id": self.project.id,
                "agile_item_type_id": self.item_type.id,
                "agile_story_points": 2,
            }
        )
        sprint = self._create_sprint([Command.set(carry_task.ids)])
        target = self._create_sprint()
        sprint.action_start()
        sprint._close_with_disposition("draft_sprint", target)
        zero_point = self.env["project.task"].create(
            {
                "name": "Zero-point completed work",
                "project_id": self.project.id,
                "agile_item_type_id": self.item_type.id,
                "agile_story_points": 0,
                "sprint_id": target.id,
                "state": "1_done",
            }
        )
        target.action_start()
        target._close_with_disposition("product_backlog")

        carried_report = self.env["project.scrum.analytics"].get_report(sprint.id)
        target_report = self.env["project.scrum.analytics"].get_report(target.id)

        self.assertFalse(carry_task.sprint_id)
        self.assertEqual(carried_report["velocity"], 0.0)
        self.assertEqual(carried_report["scope_change"]["final"], 0.0)
        self.assertEqual(target_report["scope_change"]["initial"], 2.0)
        self.assertEqual(target_report["velocity"], 0.0)
        self.assertEqual(zero_point.agile_story_points, 0.0)

    def test_same_timestamp_events_are_replayed_by_event_identifier(self):
        sprint = self._create_sprint()
        sprint.action_start()
        event_at = fields.Datetime.now()
        event_values = [
            {"event_type": "added", "story_points": 3},
            {"event_type": "completed", "story_points": 3},
            {"event_type": "reopened", "story_points": 3},
            {"event_type": "completed", "story_points": 3},
        ]
        for values in event_values:
            self.env["project.sprint.scope.event"].create(
                {
                    **values,
                    "sprint_id": sprint.id,
                    "task_id": self.task.id,
                    "actor_id": self.env.user.id,
                    "event_at": event_at,
                }
            )

        report = self.env["project.scrum.analytics"].get_report(sprint.id)

        self.assertEqual(report["burndown"]["remaining"], 0.0)
        self.assertEqual(report["burnup"], {"completed": 3.0, "total": 3.0})
        self.assertEqual(
            [point["burndown_remaining"] for point in report["timeline"]],
            [3.0, 0.0, 3.0, 0.0],
        )
        self.assertEqual(
            [point["event_id"] for point in report["timeline"]],
            sorted(point["event_id"] for point in report["timeline"]),
        )

    def test_service_enforces_project_company_and_model_access(self):
        user = mail_new_test_user(
            self.env, "Analytics user", groups="project.group_project_user"
        )
        self.project.write({"privacy_visibility": "followers"})
        self.project.message_subscribe(partner_ids=[user.partner_id.id])
        sprint = self._create_sprint([Command.set(self.task.ids)])
        sprint.action_start()
        foreign_project = self.env["project.project"].create(
            {
                "name": "Foreign analytics project",
                "privacy_visibility": "followers",
                "agile_enabled": True,
                "agile_key": "FOREIGN",
            }
        )
        foreign_team = self.env["project.agile.team"].create(
            {"name": "Foreign team", "project_id": foreign_project.id}
        )
        foreign_sprint = self.env["project.sprint"].create(
            {
                "name": "Foreign Sprint",
                "project_id": foreign_project.id,
                "team_id": foreign_team.id,
            }
        )
        foreign_sprint.action_start()
        other_company = self.env["res.company"].create({"name": "Other Company"})
        other_project = self.env["project.project"].create(
            {
                "name": "Other company project",
                "privacy_visibility": "employees",
                "company_id": other_company.id,
                "agile_enabled": True,
                "agile_key": "OTHERCOMPANY",
            }
        )
        other_team = self.env["project.agile.team"].create(
            {"name": "Other company team", "project_id": other_project.id}
        )
        other_sprint = self.env["project.sprint"].create(
            {
                "name": "Other Company Sprint",
                "project_id": other_project.id,
                "team_id": other_team.id,
            }
        )

        self.assertEqual(
            self.env["project.scrum.analytics"].with_user(user).get_report(sprint.id)["sprint"]["id"],
            sprint.id,
        )
        with self.assertRaises(AccessError):
            self.env["project.scrum.analytics"].with_user(user).get_report(foreign_sprint.id)
        with self.assertRaises(AccessError):
            self.env["project.scrum.analytics"].with_user(user).get_report(other_sprint.id)
        with self.assertRaises(AccessError):
            self.env["project.scrum.analytics"].with_user(user).get_report("not-an-id")

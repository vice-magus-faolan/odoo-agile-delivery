"""Regression coverage for the read-only Agile planning snapshot boundary."""

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestProjectAgilePlanningSnapshot(TransactionCase):
    """Exercise the current-user, bounded planning snapshot service."""

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Planning Project",
                "privacy_visibility": "employees",
                "company_id": self.env.company.id,
                "agile_enabled": True,
                "agile_key": "PLAN",
                "agile_estimation_method": "fibonacci",
            }
        )
        self.team = self.env["project.agile.team"].create(
            {"name": "Planning Team", "project_id": self.project.id}
        )
        self.eligible_type = self.env["project.agile.item.type"].create(
            {
                "name": "Planning Story",
                "code": "planning_story",
                "can_schedule_in_sprint": True,
            }
        )
        self.ineligible_type = self.env["project.agile.item.type"].create(
            {
                "name": "Planning Chore",
                "code": "planning_chore",
                "can_schedule_in_sprint": False,
            }
        )
        self.backlog_task = self._create_task("Product Backlog work", agile_story_points=5)

    def _create_task(self, name, **values):
        task_values = {
            "name": name,
            "project_id": self.project.id,
            "agile_item_type_id": self.eligible_type.id,
        }
        task_values.update(values)
        return self.env["project.task"].create(task_values)

    def _create_sprint(self, name="Sprint 1", team=False):
        return self.env["project.sprint"].create(
            {
                "name": name,
                "project_id": self.project.id,
                "team_id": (team or self.team).id,
            }
        )

    def _snapshot(self, cursor=False):
        return self.env["project.project"].get_agile_planning_snapshot(
            self.project.id, cursor
        )

    def test_snapshot_composes_authoritative_sprint_and_backlog_data(self):
        sprint = self._create_sprint()
        scheduled_task = self._create_task(
            "Committed work", agile_story_points=3, sprint_id=sprint.id
        )
        sprint.action_start()
        ineligible_task = self._create_task(
            "Unschedulable work", agile_item_type_id=self.ineligible_type.id
        )
        inactive_task = self._create_task("Archived work", active=False)

        snapshot = self._snapshot()

        self.assertEqual(snapshot["project"]["id"], self.project.id)
        self.assertEqual(snapshot["project"]["name"], self.project.display_name)
        self.assertEqual(len(snapshot["sprints"]), 1)
        sprint_data = snapshot["sprints"][0]
        self.assertEqual(sprint_data["id"], sprint.id)
        self.assertEqual(sprint_data["state"], "active")
        self.assertEqual(sprint_data["current_points"], 3)
        self.assertEqual(sprint_data["committed_points"], 3)
        backlog_ids = [item["id"] for item in snapshot["backlog"]["items"]]
        self.assertIn(self.backlog_task.id, backlog_ids)
        self.assertNotIn(scheduled_task.id, backlog_ids)
        self.assertNotIn(ineligible_task.id, backlog_ids)
        self.assertNotIn(inactive_task.id, backlog_ids)
        backlog_item = next(
            item for item in snapshot["backlog"]["items"] if item["id"] == self.backlog_task.id
        )
        self.assertEqual(backlog_item["agile_key"], self.backlog_task.agile_key)
        self.assertEqual(backlog_item["story_points"], 5)
        self.assertEqual(backlog_item["item_type"], self.eligible_type.display_name)
        self.assertIsNone(backlog_item["parent"])

    def test_snapshot_includes_active_sprints_for_multiple_active_teams(self):
        second_team = self.env["project.agile.team"].create(
            {"name": "Second Planning Team", "project_id": self.project.id}
        )
        first_sprint = self._create_sprint("First active Sprint")
        second_sprint = self._create_sprint("Second active Sprint", team=second_team)
        first_sprint.action_start()
        second_sprint.action_start()

        snapshot = self._snapshot()

        self.assertEqual(
            {sprint["id"] for sprint in snapshot["sprints"]},
            {first_sprint.id, second_sprint.id},
        )

    def test_snapshot_rejects_invalid_or_unavailable_projects_without_metadata(self):
        outsider = mail_new_test_user(self.env, "Planning outsider")

        with self.assertRaises(ValidationError):
            self.env["project.project"].get_agile_planning_snapshot(True)
        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(outsider).get_agile_planning_snapshot(
                self.project.id
            )

        self.project.active = False
        with self.assertRaises(AccessError):
            self._snapshot()

    def test_snapshot_honors_current_company_scope(self):
        other_company = self.env["res.company"].create({"name": "Other Planning Company"})
        user = mail_new_test_user(self.env, "Multi-company planner", groups="project.group_project_user")
        user.company_ids = [Command.set((self.env.company | other_company).ids)]

        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(user).with_context(
                allowed_company_ids=[other_company.id]
            ).get_agile_planning_snapshot(self.project.id)

    def test_snapshot_pages_large_backlogs_with_a_typed_cursor(self):
        for index in range(51):
            self._create_task(f"Backlog item {index}")

        first_page = self._snapshot()
        second_page = self._snapshot(first_page["backlog"]["next_cursor"])

        self.assertEqual(len(first_page["backlog"]["items"]), 50)
        self.assertTrue(first_page["backlog"]["next_cursor"])
        self.assertEqual(len(second_page["backlog"]["items"]), 2)
        self.assertFalse(second_page["backlog"]["next_cursor"])
        with self.assertRaises(ValidationError):
            self._snapshot({"id": True, "sequence": 10})

    def test_planning_action_is_project_scoped_and_read_only(self):
        action = self.project.action_open_agile_planning()

        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "project_agile_ui.planning")
        self.assertEqual(action["context"], {"project_id": self.project.id})

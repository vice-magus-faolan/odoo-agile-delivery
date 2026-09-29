"""Regression coverage for authoritative Agile planning mutations."""

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestProjectAgilePlanningActions(TransactionCase):
    """Exercise UI requests through the same current-user Scrum boundary as wizards."""

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Interactive Planning Project",
                "privacy_visibility": "employees",
                "company_id": self.env.company.id,
                "agile_enabled": True,
                "agile_key": "INTERACTIVE",
            }
        )
        self.team = self.env["project.agile.team"].create(
            {"name": "Interactive Planning Team", "project_id": self.project.id}
        )
        self.eligible_type = self.env["project.agile.item.type"].create(
            {
                "name": "Interactive Story",
                "code": "interactive_story",
                "can_schedule_in_sprint": True,
            }
        )
        self.planner = mail_new_test_user(
            self.env, "Interactive planner", groups="project.group_project_manager"
        )
        self.first_task = self._create_task("First Product Backlog item", agile_backlog_sequence=10)
        self.second_task = self._create_task("Second Product Backlog item", agile_backlog_sequence=20)
        self.sprint = self.env["project.sprint"].create(
            {
                "name": "Interactive Sprint",
                "project_id": self.project.id,
                "team_id": self.team.id,
            }
        )

    def _create_task(self, name, **values):
        task_values = {
            "name": name,
            "project_id": self.project.id,
            "agile_item_type_id": self.eligible_type.id,
        }
        task_values.update(values)
        return self.env["project.task"].create(task_values)

    def _snapshot(self):
        return self.env["project.project"].with_user(self.planner).get_agile_planning_snapshot(
            self.project.id
        )

    def _change(self, operation, task_ids, *, sprint_id=False, before_task_id=False, versions=None):
        return self.env["project.project"].with_user(self.planner).apply_agile_planning_change(
            self.project.id,
            operation,
            task_ids,
            sprint_id=sprint_id,
            before_task_id=before_task_id,
            expected_versions=versions or {},
        )

    def test_assigns_current_backlog_items_to_a_compatible_draft_sprint(self):
        snapshot = self._snapshot()
        task = next(item for item in snapshot["backlog"]["items"] if item["id"] == self.first_task.id)
        sprint = next(item for item in snapshot["sprints"] if item["id"] == self.sprint.id)

        updated = self._change(
            "assign",
            [self.first_task.id],
            sprint_id=self.sprint.id,
            versions={self.first_task.id: task["version"], self.sprint.id: sprint["version"]},
        )

        self.assertEqual(self.first_task.sprint_id, self.sprint)
        sprint_data = next(item for item in updated["sprints"] if item["id"] == self.sprint.id)
        self.assertEqual([item["id"] for item in sprint_data["items"]], [self.first_task.id])
        self.assertNotIn(self.first_task.id, [item["id"] for item in updated["backlog"]["items"]])

    def test_rejects_active_sprint_assignment_without_partial_write(self):
        self.sprint.action_start()
        snapshot = self._snapshot()
        task = next(item for item in snapshot["backlog"]["items"] if item["id"] == self.first_task.id)
        sprint = next(item for item in snapshot["sprints"] if item["id"] == self.sprint.id)

        with self.assertRaises(ValidationError):
            self._change(
                "assign",
                [self.first_task.id],
                sprint_id=self.sprint.id,
                versions={self.first_task.id: task["version"], self.sprint.id: sprint["version"]},
            )

        self.assertFalse(self.first_task.sprint_id)
        self.assertFalse(self.sprint.scope_event_ids)

    def test_rejects_stale_assignment_without_partial_write(self):
        snapshot = self._snapshot()
        task = next(item for item in snapshot["backlog"]["items"] if item["id"] == self.first_task.id)
        sprint = next(item for item in snapshot["sprints"] if item["id"] == self.sprint.id)
        self.first_task.write({"name": "Changed after snapshot"})

        with self.assertRaises(ValidationError):
            self._change(
                "assign",
                [self.first_task.id],
                sprint_id=self.sprint.id,
                versions={self.first_task.id: task["version"], self.sprint.id: sprint["version"]},
            )

        self.assertFalse(self.first_task.sprint_id)

    def test_reorders_the_current_backlog_under_server_preconditions(self):
        snapshot = self._snapshot()
        first = next(item for item in snapshot["backlog"]["items"] if item["id"] == self.first_task.id)
        second = next(item for item in snapshot["backlog"]["items"] if item["id"] == self.second_task.id)

        updated = self._change(
            "reorder",
            [self.second_task.id],
            before_task_id=self.first_task.id,
            versions={self.second_task.id: second["version"], self.first_task.id: first["version"]},
        )

        self.assertEqual(
            [item["id"] for item in updated["backlog"]["items"][:2]],
            [self.second_task.id, self.first_task.id],
        )
        self.assertLess(self.second_task.agile_backlog_sequence, self.first_task.agile_backlog_sequence)

    def test_rejects_unreadable_selected_tasks_before_any_mutation(self):
        other_company = self.env["res.company"].create({"name": "Unrelated Planning Company"})
        other_project = self.env["project.project"].create(
            {
                "name": "Unrelated Planning Project",
                "privacy_visibility": "employees",
                "company_id": other_company.id,
                "agile_enabled": True,
                "agile_key": "UNRELATED",
            }
        )
        other_task = self.env["project.task"].create(
            {
                "name": "Unrelated Product Backlog item",
                "project_id": other_project.id,
                "agile_item_type_id": self.eligible_type.id,
            }
        )

        with self.assertRaises(AccessError):
            self._change("assign", [self.first_task.id, other_task.id], sprint_id=self.sprint.id)

        self.assertFalse(self.first_task.sprint_id)

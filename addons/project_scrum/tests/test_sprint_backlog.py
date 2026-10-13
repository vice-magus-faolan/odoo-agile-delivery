from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestProjectSprintBacklog(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Scrum Project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "SCRUM",
            }
        )
        self.team = self.env["project.agile.team"].create(
            {"name": "Delivery Team", "project_id": self.project.id}
        )
        self.eligible_type = self.env["project.agile.item.type"].create(
            {
                "name": "Eligible Story",
                "code": "test_eligible_story",
                "can_schedule_in_sprint": True,
            }
        )
        self.ineligible_type = self.env["project.agile.item.type"].create(
            {
                "name": "Ineligible Task",
                "code": "test_ineligible_task",
                "can_schedule_in_sprint": False,
            }
        )
        self.task = self._create_task("Product Backlog work")

    def _create_task(self, name, **values):
        task_values = {
            "name": name,
            "project_id": self.project.id,
            "agile_item_type_id": self.eligible_type.id,
        }
        task_values.update(values)
        return self.env["project.task"].create(task_values)

    def _create_sprint(self, name="Sprint 1"):
        return self.env["project.sprint"].create(
            {
                "name": name,
                "project_id": self.project.id,
                "team_id": self.team.id,
            }
        )

    def _create_wizard(self, tasks, operation, sprint=False):
        values = {
            "task_ids": [Command.set(tasks.ids)],
            "project_id": self.project.id,
            "operation": operation,
        }
        if sprint:
            values["sprint_id"] = sprint.id
        return self.env["project.sprint.task.assignment.wizard"].create(values)

    def test_product_backlog_action_is_project_scoped_and_sprint_eligible(self):
        sprint = self._create_sprint()
        foreign_project = self.env["project.project"].create(
            {
                "name": "Other Scrum Project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "OTHER",
            }
        )
        foreign_task = self.env["project.task"].create(
            {
                "name": "Other product backlog work",
                "project_id": foreign_project.id,
                "agile_item_type_id": self.eligible_type.id,
            }
        )
        ineligible_task = self._create_task(
            "Unschedulable work", agile_item_type_id=self.ineligible_type.id
        )
        scheduled_task = self._create_task("Scheduled work", sprint_id=sprint.id)

        action = sprint.action_open_product_backlog()
        task_ids = self.env["project.task"].search(action["domain"])

        self.assertEqual(task_ids, self.task)
        self.assertNotIn(foreign_task, task_ids)
        self.assertNotIn(ineligible_task, task_ids)
        self.assertNotIn(scheduled_task, task_ids)
        self.assertEqual(action["context"]["default_project_id"], self.project.id)

    def test_sprint_backlog_action_returns_only_the_selected_sprint_tasks(self):
        sprint = self._create_sprint()
        other_sprint = self._create_sprint("Sprint 2")
        sprint_task = self._create_task("Current Sprint work", sprint_id=sprint.id)
        other_sprint_task = self._create_task(
            "Other Sprint work", sprint_id=other_sprint.id
        )

        action = sprint.action_open_sprint_backlog()
        task_ids = self.env["project.task"].search(action["domain"])

        self.assertEqual(task_ids, sprint_task)
        self.assertNotIn(other_sprint_task, task_ids)

    def test_server_actions_open_the_assignment_wizard_for_the_selected_tasks(self):
        assign_action = (
            self.env.ref("project_scrum.action_assign_tasks_to_sprint")
            .with_context(active_model="project.task", active_ids=self.task.ids)
            .run()
        )
        remove_action = (
            self.env.ref("project_scrum.action_remove_tasks_from_sprint")
            .with_context(active_model="project.task", active_ids=self.task.ids)
            .run()
        )

        self.assertEqual(
            assign_action["res_model"], "project.sprint.task.assignment.wizard"
        )
        self.assertEqual(assign_action["context"]["default_operation"], "assign")
        self.assertEqual(
            remove_action["res_model"], "project.sprint.task.assignment.wizard"
        )
        self.assertEqual(remove_action["context"]["default_operation"], "remove")

    def test_assign_wizard_adds_active_sprint_scope_event(self):
        sprint = self._create_sprint()
        sprint.action_start()

        self._create_wizard(self.task, "assign", sprint).action_confirm()

        self.assertEqual(self.task.sprint_id, sprint)
        self.assertEqual(sprint.scope_event_ids.mapped("event_type"), ["added"])
        self.assertEqual(sprint.scope_event_ids.task_id, self.task)

    def test_remove_wizard_removes_from_active_sprint_and_records_scope_event(self):
        sprint = self._create_sprint()
        sprint.action_start()
        self.task.write({"sprint_id": sprint.id})

        self._create_wizard(self.task, "remove").action_confirm()

        self.assertFalse(self.task.sprint_id)
        self.assertEqual(
            sprint.scope_event_ids.mapped("event_type"), ["added", "removed"]
        )

    def test_assign_wizard_rejects_an_ineligible_item_type(self):
        sprint = self._create_sprint()
        task = self._create_task(
            "Ineligible work", agile_item_type_id=self.ineligible_type.id
        )

        with self.assertRaises(ValidationError):
            self._create_wizard(task, "assign", sprint).action_confirm()

        self.assertFalse(task.sprint_id)

    def test_assign_wizard_rejects_a_closed_sprint(self):
        sprint = self._create_sprint()
        sprint.action_start()
        sprint.action_close()

        with self.assertRaises(ValidationError):
            self._create_wizard(self.task, "assign", sprint).action_confirm()

        self.assertFalse(self.task.sprint_id)

    def test_assign_wizard_rejects_mixed_scheduled_and_unscheduled_tasks(self):
        sprint = self._create_sprint()
        already_scheduled = self._create_task("Scheduled work", sprint_id=sprint.id)

        with self.assertRaises(ValidationError):
            self._create_wizard(
                self.task | already_scheduled, "assign", sprint
            ).action_confirm()

        self.assertFalse(self.task.sprint_id)
        self.assertEqual(already_scheduled.sprint_id, sprint)

    def test_assignment_wizard_rejects_cross_project_task_selection(self):
        foreign_project = self.env["project.project"].create(
            {
                "name": "Other Scrum Project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "OTHER",
            }
        )
        foreign_task = self.env["project.task"].create(
            {
                "name": "Other work",
                "project_id": foreign_project.id,
                "agile_item_type_id": self.eligible_type.id,
            }
        )

        with self.assertRaises(ValidationError):
            self._create_wizard(
                self.task | foreign_task, "assign", self._create_sprint()
            )

    def test_typeless_agile_task_cannot_bypass_product_backlog_eligibility(self):
        sprint = self._create_sprint()
        task = self._create_task("Typeless work", agile_item_type_id=False)

        with self.assertRaises(ValidationError):
            task.write({"sprint_id": sprint.id})

        self.assertFalse(task.sprint_id)

    def test_scheduled_item_type_cannot_become_ineligible(self):
        sprint = self._create_sprint()
        self.task.write({"sprint_id": sprint.id})

        with self.assertRaises(ValidationError):
            self.eligible_type.write({"can_schedule_in_sprint": False})

        self.assertTrue(self.eligible_type.can_schedule_in_sprint)

    def test_project_user_cannot_create_the_assignment_wizard(self):
        user = mail_new_test_user(
            self.env, "Scrum user", groups="project.group_project_user"
        )

        with self.assertRaises(AccessError):
            self.env["project.sprint.task.assignment.wizard"].with_user(user).create(
                {
                    "task_ids": [Command.set(self.task.ids)],
                    "project_id": self.project.id,
                    "operation": "remove",
                }
            )

from unittest.mock import patch

from odoo import SUPERUSER_ID
from odoo import Command, fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestProjectScrumDomain(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Scrum Project",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "SCRUM",
                "agile_estimation_method": "fibonacci",
            }
        )
        self.team = self.env["project.agile.team"].create(
            {"name": "Delivery Team", "project_id": self.project.id}
        )
        self.sprint_item_type = self.env["project.agile.item.type"].create(
            {"name": "Sprint Story", "code": "test_sprint_story", "can_schedule_in_sprint": True}
        )
        self.task = self.env["project.task"].create(
            {
                "name": "Committed work",
                "project_id": self.project.id,
                "agile_item_type_id": self.sprint_item_type.id,
                "agile_story_points": 5,
            }
        )

    def _create_sprint(self, name, team=None, task_ids=None):
        return self.env["project.sprint"].create(
            {
                "name": name,
                "project_id": self.project.id,
                "team_id": (team or self.team).id,
                "task_ids": task_ids or [],
            }
        )

    def test_start_records_immutable_committed_scope(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])

        sprint.action_start()

        self.assertEqual(sprint.state, "active")
        self.assertEqual(sprint.committed_task_ids, self.task)
        events = self.env["project.sprint.scope.event"].search([("sprint_id", "=", sprint.id)])
        self.assertEqual(events.mapped("event_type"), ["committed"])
        self.assertEqual(events.task_id, self.task)
        self.assertEqual(events.story_points, 5)

    def test_only_one_team_sprint_can_be_active_per_project(self):
        first = self._create_sprint("Sprint 1")
        second = self._create_sprint("Sprint 2")
        other_team = self.env["project.agile.team"].create(
            {"name": "Platform Team", "project_id": self.project.id}
        )
        parallel = self._create_sprint("Sprint 3", team=other_team)

        first.action_start()
        with self.assertRaises(ValidationError):
            second.action_start()
        parallel.action_start()

        self.assertEqual((first.state, parallel.state), ("active", "active"))

    def test_lifecycle_state_cannot_bypass_start_action(self):
        sprint = self._create_sprint("Sprint 1")
        manager = mail_new_test_user(self.env, "Sprint manager", groups="project.group_project_manager")

        with self.assertRaises(ValidationError):
            sprint.write({"state": "active"})
        with self.assertRaises(ValidationError):
            sprint.with_user(manager).with_context(
                project_scrum_lifecycle_transition=True
            ).write({"state": "active"})
        with self.assertRaises(ValidationError):
            self.env["project.sprint"].create(
                {
                    "name": "Bypassed Sprint",
                    "project_id": self.project.id,
                    "team_id": self.team.id,
                    "state": "active",
                }
            )

        self.assertEqual(sprint.state, "draft")


    def test_project_user_cannot_start_sprint(self):
        user = mail_new_test_user(self.env, "Scrum user", groups="project.group_project_user")
        sprint = self._create_sprint("Sprint 1")

        with self.assertRaises(AccessError):
            sprint.with_user(user).action_start()

        self.assertEqual(sprint.state, "draft")
        self.assertFalse(sprint.committed_task_ids)
        self.assertFalse(sprint.scope_event_ids)

    def test_project_user_cannot_close_sprint(self):
        user = mail_new_test_user(self.env, "Scrum user", groups="project.group_project_user")
        sprint = self._create_sprint("Sprint 1")
        sprint.action_start()

        with self.assertRaises(AccessError):
            sprint.with_user(user).action_close()

        self.assertEqual(sprint.state, "active")


    def test_active_sprint_records_post_start_adds_and_removals(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        added = self.env["project.task"].create({"name": "Added after start", "project_id": self.project.id, "agile_item_type_id": self.sprint_item_type.id, "agile_story_points": 3, "sprint_id": sprint.id})

        added.write({"sprint_id": False})

        events = self.env["project.sprint.scope.event"].search([("sprint_id", "=", sprint.id)], order="event_at, id")
        self.assertEqual(events.mapped("event_type"), ["committed", "added", "removed"])
        self.assertEqual(events.mapped("task_id"), self.task | added | added)
        self.assertEqual(events.mapped("story_points"), [5, 3, 3])

    def test_active_sprint_records_native_done_and_reopen_edges_once(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        sprint.action_start()

        self.task.write({"state": "1_done"})
        self.task.write({"state": "1_done"})
        self.task.write({"state": "01_in_progress"})
        self.task.write({"state": "01_in_progress"})

        events = self.env["project.sprint.scope.event"].search(
            [("sprint_id", "=", sprint.id)], order="event_at, id"
        )
        self.assertEqual(events.mapped("event_type"), ["committed", "completed", "reopened"])
        self.assertEqual(events.mapped("task_id"), self.task | self.task | self.task)
        self.assertEqual(events.mapped("story_points"), [5, 5, 5])

    def test_active_sprint_records_bulk_native_done_edges(self):
        second_task = self.env["project.task"].create(
            {"name": "Second work item", "project_id": self.project.id, "agile_item_type_id": self.sprint_item_type.id, "agile_story_points": 3}
        )
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set((self.task | second_task).ids)])
        sprint.action_start()

        (self.task | second_task).write({"state": "1_done"})

        completed_events = sprint.scope_event_ids.filtered(lambda event: event.event_type == "completed")
        self.assertEqual(completed_events.task_id, self.task | second_task)
        self.assertEqual(completed_events.mapped("story_points"), [5, 3])

    def test_project_user_native_done_write_records_the_actual_actor(self):
        user = mail_new_test_user(self.env, "Scrum user", groups="project.group_project_user")
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        sprint.action_start()

        self.task.with_user(user).write({"state": "1_done"})

        completed_event = sprint.scope_event_ids.filtered(lambda event: event.event_type == "completed")
        self.assertEqual(completed_event.actor_id, user)

    def test_closed_sprint_freezes_completion_history(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        self.task.write({"state": "1_done"})
        self.assertTrue(sprint.action_close())

        self.task.write({"state": "01_in_progress"})

        self.assertEqual(
            sprint.scope_event_ids.mapped("event_type"), ["committed", "completed"]
        )


    def test_task_sprint_assignment_rejects_cross_project_assignment(self):
        sprint = self._create_sprint("Sprint 1")
        foreign_project = self.env["project.project"].create({"name": "Other Scrum Project", "privacy_visibility": "employees", "agile_enabled": True, "agile_key": "OTHER"})
        foreign_task = self.env["project.task"].create({"name": "Foreign work", "project_id": foreign_project.id})

        with self.assertRaises(ValidationError):
            foreign_task.write({"sprint_id": sprint.id})

        self.assertFalse(foreign_task.sprint_id)

    def test_ordinary_project_task_keeps_native_behavior_without_a_sprint(self):
        ordinary_project = self.env["project.project"].create({"name": "Ordinary", "privacy_visibility": "employees"})
        task = self.env["project.task"].create({"name": "Ordinary task", "project_id": ordinary_project.id})

        task.write({"name": "Renamed ordinary task"})

        self.assertFalse(task.sprint_id)
        self.assertEqual(task.name, "Renamed ordinary task")


    def test_project_users_can_read_but_not_administer_scrum_records(self):
        user = mail_new_test_user(self.env, "Scrum user", groups="project.group_project_user")

        self.team.with_user(user).read(["name"])
        with self.assertRaises(AccessError):
            self.env["project.agile.team"].with_user(user).create({"name": "Unauthorized", "project_id": self.project.id})
        with self.assertRaises(AccessError):
            self.env["project.sprint"].with_user(user).create({"name": "Unauthorized", "project_id": self.project.id, "team_id": self.team.id})

    def test_scope_events_are_immutable_for_project_managers(self):
        manager = mail_new_test_user(self.env, "Scrum manager", groups="project.group_project_manager")
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        event = sprint.scope_event_ids

        with self.assertRaises(AccessError):
            event.with_user(manager).write({"reason": "rewrite history"})
        with self.assertRaises(AccessError):
            event.with_user(manager).unlink()
        with self.assertRaises(AccessError):
            self.env["project.sprint.scope.event"].with_user(manager).with_context(
                project_scrum_allow_event_create=True
            ).create(
                {
                    "sprint_id": sprint.id,
                    "task_id": self.task.id,
                    "event_type": "added",
                    "story_points": self.task.agile_story_points,
                    "actor_id": manager.id,
                    "event_at": fields.Datetime.now(),
                }
            )


    def test_task_sprint_assignment_rejects_cross_company_assignment(self):
        sprint = self._create_sprint("Sprint 1")
        other_company = self.env["res.company"].create({"name": "Other company"})

        with self.assertRaises(ValidationError):
            self.task.write({"company_id": other_company.id, "sprint_id": sprint.id})

        self.assertFalse(self.task.sprint_id)


    def test_standard_scrum_views_and_actions_are_installed(self):
        for xml_id in ("project_scrum.view_project_agile_team_form", "project_scrum.view_project_sprint_form", "project_scrum.view_task_form_scrum", "project_scrum.view_task_list_scrum", "project_scrum.view_task_search_scrum", "project_scrum.action_project_sprint", "project_scrum.action_project_agile_team"):
            self.assertTrue(self.env.ref(xml_id))

        action = self.env.ref("project_scrum.action_project_sprint")
        self.assertEqual(action.res_model, "project.sprint")
        self.assertIn("list", action.view_mode)

    def _close_with_wizard(self, sprint, disposition, target_sprint=False):
        action = sprint.action_close()
        self.assertEqual(action["res_model"], "project.sprint.close.wizard")
        values = {"sprint_id": sprint.id, "unfinished_disposition": disposition}
        if target_sprint:
            values["target_sprint_id"] = target_sprint.id
        return self.env["project.sprint.close.wizard"].create(values).action_confirm()

    def test_close_with_backlog_disposition_records_distinct_fact(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        sprint.action_start()

        self.assertTrue(self._close_with_wizard(sprint, "product_backlog"))

        self.assertEqual(sprint.state, "closed")
        self.assertFalse(self.task.sprint_id)
        self.assertEqual(sprint.committed_task_ids, self.task)
        self.assertEqual(
            sprint.scope_event_ids.mapped("event_type"), ["committed", "carried_to_backlog"]
        )

    def test_close_with_draft_target_records_linked_carry_over(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        target = self._create_sprint("Sprint 2")
        sprint.action_start()

        self.assertTrue(self._close_with_wizard(sprint, "draft_sprint", target))

        carry_over = sprint.scope_event_ids.filtered(
            lambda event: event.event_type == "carried_to_sprint"
        )
        self.assertEqual(sprint.state, "closed")
        self.assertEqual(self.task.sprint_id, target)
        self.assertEqual(carry_over.task_id, self.task)
        self.assertEqual(carry_over.carryover_target_sprint_id, target)
        self.assertFalse(target.committed_task_ids)

    def test_close_rejects_incompatible_targets_without_partial_changes(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        other_team = self.env["project.agile.team"].create(
            {"name": "Other Team", "project_id": self.project.id}
        )
        incompatible = self._create_sprint("Other team Sprint", team=other_team)
        sprint.action_start()

        with self.assertRaises(ValidationError):
            self._close_with_wizard(sprint, "draft_sprint", incompatible)

        self.assertEqual(sprint.state, "active")
        self.assertEqual(self.task.sprint_id, sprint)
        self.assertFalse(incompatible.task_ids)
        self.assertEqual(sprint.scope_event_ids.mapped("event_type"), ["committed"])

    def test_close_rejects_self_and_active_targets(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        other_team = self.env["project.agile.team"].create(
            {"name": "Other Team", "project_id": self.project.id}
        )
        active_target = self._create_sprint("Active Sprint", team=other_team)
        sprint.action_start()
        active_target.action_start()

        with self.assertRaises(ValidationError):
            self._close_with_wizard(sprint, "draft_sprint", sprint)
        with self.assertRaises(ValidationError):
            self._close_with_wizard(sprint, "draft_sprint", active_target)

        self.assertEqual(sprint.state, "active")
        self.assertEqual(self.task.sprint_id, sprint)

    def test_close_rolls_back_when_moving_unfinished_tasks_fails(self):
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        sprint.action_start()

        with patch.object(
            type(sprint), "_move_unfinished_tasks", side_effect=ValidationError("forced failure")
        ):
            with self.assertRaises(ValidationError):
                self._close_with_wizard(sprint, "product_backlog")

        self.assertEqual(sprint.state, "active")
        self.assertEqual(self.task.sprint_id, sprint)
        self.assertEqual(sprint.scope_event_ids.mapped("event_type"), ["committed"])

    def test_closed_sprint_blocks_normal_assignment_and_manager_mutation(self):
        manager = mail_new_test_user(
            self.env, "Sprint manager", groups="project.group_project_manager"
        )
        sprint = self._create_sprint("Sprint 1", task_ids=[Command.set(self.task.ids)])
        sprint.action_start()
        self.task.write({"state": "1_done"})
        sprint.action_close()

        with self.assertRaises(ValidationError):
            self.task.with_user(manager).write({"sprint_id": False})
        with self.assertRaises(ValidationError):
            sprint.with_user(manager).write({"goal": "rewrite history"})

        sprint.with_user(SUPERUSER_ID).write({"goal": "documented recovery"})
        self.assertEqual(sprint.goal, "documented recovery")

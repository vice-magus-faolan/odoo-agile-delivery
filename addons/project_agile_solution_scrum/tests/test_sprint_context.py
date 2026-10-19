"""Native event semantics and exact frozen requirement context, never live aliases."""

import json
from types import SimpleNamespace
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval

from odoo.addons.project_agile_solution.tests.test_solution_task_trace import (
    TestSolutionTaskTrace,
)


class TestSolutionSprintContext(TestSolutionTaskTrace):
    def _sprint(self):
        self.project.with_user(self.manager).write(
            {"agile_estimation_method": "fibonacci"}
        )
        team = (
            self.env["project.agile.team"]
            .with_user(self.manager)
            .create({"name": "SYNTHETIC team", "project_id": self.project.id})
        )
        return (
            self.env["project.sprint"]
            .with_user(self.manager)
            .create(
                {
                    "name": "SYNTHETIC timebox",
                    "project_id": self.project.id,
                    "team_id": team.id,
                }
            )
        )

    def _events(self, task, event_type):
        return (
            self.env["project.sprint.scope.event"]
            .with_user(self.manager)
            .search([("task_id", "=", task.id), ("event_type", "=", event_type)])
        )

    def _contexts(self, event):
        return (
            self.env["project.agile.solution.sprint.context"]
            .with_user(self.manager)
            .search([("scope_event_id", "in", event.ids)])
        )

    def test_start_freezes_actual_v1_later_addition_captures_v2_and_close_retains_both(
        self,
    ):
        requirement, task = self._requirement(), self._task()
        edge = self._link(requirement, task)
        sprint = self._sprint()
        task.write({"sprint_id": sprint.id, "agile_story_points": 3})
        sprint.action_start()
        committed = self._events(task, "committed")
        frozen = self._contexts(committed).payload_json
        self.assertEqual(committed.solution_capture_status, "captured")
        self.assertEqual(
            json.loads(frozen)["requirement"]["revision_id"], requirement.id
        )
        self.assertEqual(sprint.committed_task_ids, task)
        successor = requirement.browse(
            requirement.requirement_id.action_new_revision()["res_id"]
        )
        successor.write({"acceptance_expectations": "Explicit later evaluation"})
        edge.action_retire("Deliberate successor coverage")
        self._link(successor, task)
        requirement.requirement_id.write({"active": False})
        self.assertEqual(self._contexts(committed).payload_json, frozen)
        # Existing linked archived identity remains navigable history but new
        # active links require an active identity.
        requirement.requirement_id.write({"active": True})
        second = self._task()
        self._link(successor, second)
        second.write({"sprint_id": sprint.id})
        added = self._events(second, "added")
        self.assertEqual(
            json.loads(self._contexts(added).payload_json)["requirement"][
                "revision_id"
            ],
            successor.id,
        )
        sprint._close_with_disposition("product_backlog")
        self.assertEqual(sprint.state, "closed")
        self.assertEqual(self._contexts(committed).payload_json, frozen)
        self.assertEqual(
            self._contexts(
                self._events(task, "carried_to_backlog")
            ).requirement_revision_id,
            successor,
        )
        self.assertEqual(committed.story_points, 3)
        self.assertEqual(sprint.committed_task_ids, task)

    def test_revision_change_before_start_captures_only_current_explicit_edges(self):
        requirement, task = self._requirement(), self._task()
        first = self._link(requirement, task)
        successor = requirement.browse(
            requirement.requirement_id.action_new_revision()["res_id"]
        )
        first.action_retire("Before commitment")
        self._link(successor, task)
        sprint = self._sprint()
        task.write({"sprint_id": sprint.id})
        sprint.action_start()
        self.assertEqual(
            self._contexts(self._events(task, "committed")).requirement_revision_id,
            successor,
        )
        self.assertTrue(successor.sealed)

    def test_empty_vs_prebridge_markers_and_no_backfill(self):
        task, sprint = self._task(), self._sprint()
        old = (
            self.env["project.sprint.scope.event"]
            .sudo()
            .create(
                {
                    "sprint_id": sprint.id,
                    "task_id": task.id,
                    "event_type": "added",
                    "story_points": 0,
                    "actor_id": self.manager.id,
                    "event_at": "2026-01-01 00:00:00",
                }
            )
        )
        self.assertEqual(old.solution_capture_status, "not_available")
        task.write(
            {
                "solution_maintenance_reason": "SYNTHETIC dependency upkeep",
                "sprint_id": sprint.id,
            }
        )
        sprint.action_start()
        committed = self._events(task, "committed")
        self.assertEqual(committed.solution_capture_status, "empty")
        self._link(self._requirement(), task)
        self.assertFalse(self._contexts(old | committed))
        self.assertEqual(old.solution_capture_status, "not_available")
        self.assertEqual(committed.solution_capture_status, "empty")

    def test_remove_complete_reopen_reestimate_and_carryover_observe_exact_context(
        self,
    ):
        requirement, task, sprint = self._requirement(), self._task(), self._sprint()
        self._link(requirement, task)
        task.write({"sprint_id": sprint.id})
        sprint.action_start()
        task.write({"agile_story_points": 5})
        task.with_user(self.user).write({"state": "1_done"})
        task.with_user(self.user).write({"state": "01_in_progress"})
        task.write({"sprint_id": False})
        for event_type in (
            "committed",
            "reestimated",
            "completed",
            "reopened",
            "removed",
        ):
            event = self._events(task, event_type)
            self.assertEqual(len(event), 1)
            self.assertEqual(event.solution_capture_status, "captured")
            self.assertEqual(self._contexts(event).requirement_revision_id, requirement)
        self.assertEqual(self._events(task, "reestimated").previous_story_points, 0)
        self.assertEqual(self._events(task, "completed").story_points, 5)

    def test_draft_specification_is_labelled_not_approved_by_commitment(self):
        requirement, task = self._requirement(), self._task()
        spec = self._revision(requirement_revision_ids=[Command.set(requirement.ids)])
        self._link(requirement, task, document_revision_id=spec.id)
        sprint = self._sprint()
        task.write({"sprint_id": sprint.id})
        sprint.action_start()
        context = self._contexts(self._events(task, "committed"))
        self.assertEqual(
            json.loads(context.payload_json)["specification"]["state"], "draft"
        )
        self.assertEqual(spec.state, "draft")
        self._approve(spec)
        self.assertEqual(
            json.loads(context.payload_json)["specification"]["state"], "draft"
        )

    def test_hidden_link_requirement_or_task_cannot_leak_or_silently_capture_empty(
        self,
    ):
        requirement, task, sprint = self._requirement(), self._task(), self._sprint()
        self._link(requirement, task)
        task.write({"sprint_id": sprint.id})
        rule = self._hide("project.agile.requirement.revision", requirement)
        with self.assertRaises(AccessError):
            sprint.action_start()
        self.assertEqual(sprint.state, "draft")
        self.assertFalse(sprint.committed_task_ids)
        self.assertFalse(
            self.env["project.sprint.scope.event"].search(
                [("sprint_id", "=", sprint.id)]
            )
        )
        rule.unlink()
        sprint.action_start()
        event = self._events(task, "committed")
        context = self._contexts(event)
        self.assertEqual(len(event), 1)
        self.assertEqual(event.solution_capture_status, "captured")
        self.assertEqual(len(context), 1)
        self._hide("project.task", task)
        self.assertNotIn(event, event.search([]))
        self.assertNotIn(context, context.search([]))
        with self.assertRaises(AccessError):
            context.read(["payload_json"])
        with self.assertRaises(AccessError):
            event.export_data(["task_id", "solution_capture_status"])

    def test_hidden_event_and_sprint_filter_context_relations_and_exports(self):
        requirement, task, sprint = self._requirement(), self._task(), self._sprint()
        self._link(requirement, task)
        task.write({"sprint_id": sprint.id})
        sprint.action_start()
        event = self._events(task, "committed")
        context = self._contexts(event)
        self.assertEqual(len(context), 1)
        for model, record in (
            ("project.sprint.scope.event", event),
            ("project.sprint", sprint),
        ):
            rule = self._hide(model, record)
            self.assertNotIn(context, context.search([]))
            with self.assertRaises(AccessError):
                context.read(["scope_event_id", "task_id"])
            with self.assertRaises(AccessError):
                context.export_data(["scope_event_id"])
            rule.unlink()
            self.assertIn(context, context.search([]))

    def test_capture_fields_context_and_snapshots_are_not_forgeable_even_sudo(self):
        requirement, task, sprint = self._requirement(), self._task(), self._sprint()
        self._link(requirement, task)
        task.write({"sprint_id": sprint.id})
        sprint.action_start()
        event = self._events(task, "committed")
        context = self._contexts(event)
        for record in (context, context.sudo()):
            with self.assertRaises(ValidationError):
                record.write({"task_id": self._task().id})
            with self.assertRaises(ValidationError):
                record.unlink()
        with self.assertRaises(AccessError):
            context.sudo().create({"scope_event_id": event.id})
        with self.assertRaises(ValidationError):
            event.sudo().write({"solution_capture_status": "empty"})
        with self.assertRaises(AccessError):
            context.read(["_payload"])
        with self.assertRaises(AccessError):
            self.env["project.agile.solution.sprint.context"].with_user(
                self.portal
            ).search([])

    def test_event_rule_denies_partial_registry_without_losing_current_closure(self):
        rule = self.env.ref("project_agile_solution_scrum.scope_event_reference_rule")
        # Expression branch coverage only. Real dependency-ordered registry
        # rebuild and native security behavior are proved by scripts/verify.
        partial_user = SimpleNamespace(
            env={"project.sprint.scope.event": SimpleNamespace(_fields={})}
        )
        partial_domain = safe_eval(rule.domain_force, {"user": partial_user})
        self.assertEqual(partial_domain, [("id", "=", 0)])
        # Compile and execute the fallback through real Odoo too, rather than
        # merely comparing a legacy domain shape that Odoo 19 rejects.
        self.assertFalse(
            self.env["project.sprint.scope.event"]
            .with_user(self.manager)
            .search(partial_domain)
        )
        self.assertEqual(
            safe_eval(rule.domain_force, {"user": self.env.user}),
            [("solution_native_access", "=", True)],
        )
        requirement, task, sprint = self._requirement(), self._task(), self._sprint()
        self._link(requirement, task)
        task.write({"sprint_id": sprint.id})
        sprint.action_start()
        self.assertEqual(len(self._events(task, "committed")), 1)

    def test_failure_mid_capture_rolls_back_assignment_native_event_and_context(self):
        requirement, task, sprint = self._requirement(), self._task(), self._sprint()
        self._link(requirement, task)
        sprint.action_start()
        model = self.env["project.agile.solution.sprint.context"]
        original = type(model)._capture

        def fail(record, event, links):
            original(record, event, links)
            # Exact synthetic fault-injection text is not a user-facing translation.
            raise ValidationError(  # pylint: disable=translation-required
                "SYNTHETIC mid-capture failure"
            )

        with patch.object(type(model), "_capture", fail):
            # Direct Python callers get the same transaction protection as RPC.
            with self.assertRaises(ValidationError):
                task.write({"sprint_id": sprint.id})
        self.assertFalse(task.sprint_id)
        self.assertFalse(self._events(task, "added"))
        self.assertFalse(model.search([("task_id", "=", task.id)]))

    def test_native_combined_role_assignment_keeps_approval_separate(self):
        analyst = self.env.ref("project_agile_solution.group_business_analyst")
        master = self.env.ref("project_scrum.group_scrum_master")
        hierarchy = self.env["res.groups"]._get_view_group_hierarchy()
        for group in (analyst, master):
            privilege = group.privilege_id
            self.assertEqual(
                hierarchy["groups"][group.id]["privilege_id"], privilege.id
            )
            self.assertIn(group.id, hierarchy["privileges"][privilege.id]["group_ids"])
        self.user.write(
            {"group_ids": [Command.link(analyst.id), Command.link(master.id)]}
        )
        self.assertTrue(
            self.user.has_group("project_agile_solution.group_business_analyst")
        )
        self.assertTrue(self.user.has_group("project_scrum.group_scrum_master"))
        self.assertFalse(self.user.has_group("project.group_project_manager"))
        requirement, task = self._requirement(), self._task()
        self._link(requirement, task)
        requirement.requirement_id.with_user(self.user).write(
            {"name": "Combined author"}
        )
        team = (
            self.env["project.agile.team"]
            .with_user(self.user)
            .create(
                {
                    "name": "Combined team",
                    "project_id": self.project.id,
                }
            )
        )
        sprint = (
            self.env["project.sprint"]
            .with_user(self.user)
            .create(
                {
                    "name": "Combined Sprint",
                    "project_id": self.project.id,
                    "team_id": team.id,
                }
            )
        )
        task.with_user(self.user).write({"sprint_id": sprint.id})
        sprint.action_start()
        events = self._events(task, "committed")
        self.assertEqual(events.solution_capture_status, "captured")
        task.with_user(self.user).write({"state": "1_done"})
        sprint.action_close()
        self.assertEqual(sprint.state, "closed")
        revision = self._revision()
        revision.with_user(self.user).action_submit()
        with self.assertRaises(AccessError):
            revision.with_user(self.user).action_approve()
        self.user.write(
            {
                "group_ids": [
                    Command.link(self.env.ref("project.group_project_manager").id)
                ]
            }
        )
        self.assertTrue(self.user.has_group("project.group_project_manager"))
        revision.document_id.write({"approver_id": self.user.id})
        revision.with_user(self.user).action_approve()
        self.assertEqual(revision.approved_by_id, self.user)

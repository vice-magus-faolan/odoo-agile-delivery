"""Cumulative nonadmin, scope, bounded-query and no-partial-state contracts."""

import logging
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.project_agile_solution.models import solution_coverage

from .test_solution_rendering import TestSolutionRendering

_logger = logging.getLogger(__name__)


class TestSolutionHardening(TestSolutionRendering):
    def test_cardinality_deny_query_is_bounded_and_uses_real_caller_orm(self):
        task = self._spike(item_type="story")
        model = self.env["project.task"].with_user(self.user)
        original = type(model).search_count
        calls = []

        def bounded_count(record, domain, limit=None):
            calls.append(limit)
            self.assertEqual(limit, solution_coverage.LIMIT + 1)
            return original(record, domain, limit=limit)

        with patch.object(type(model), "search_count", bounded_count):
            rows = solution_coverage.complete_rows(
                model.env, model._name, [("id", "=", task.id)]
            )
        self.assertEqual(rows, task)
        self.assertFalse(rows.env.su)
        self.assertEqual(rows.env.uid, self.user.id)
        self.assertEqual(calls, [solution_coverage.LIMIT + 1])

    def test_collection_limit_and_hidden_rows_fail_without_partial_metadata(self):
        tasks = (
            self.env["project.task"]
            .with_user(self.manager)
            .create(
                [
                    {
                        "name": f"SYNTHETIC bounded collection {index}",
                        "project_id": self.project.id,
                        "agile_item_type_id": self.env.ref(
                            "project_agile.project_agile_item_type_story"
                        ).id,
                    }
                    for index in range(4)
                ]
            )
        )
        domain = [("id", "in", tasks.ids)]
        caller_env = tasks.with_user(self.user).env
        with patch.object(solution_coverage, "LIMIT", 3):
            with self.assertRaises(ValidationError):
                solution_coverage.complete_rows(caller_env, tasks._name, domain)
            exact = solution_coverage.complete_rows(
                caller_env, tasks._name, [("id", "in", tasks[:3].ids)]
            )
            self.assertEqual(exact, tasks[:3])
            hidden_name = tasks[-1].name
            self._hide(tasks._name, tasks[-1])
            with self.assertRaises(AccessError) as error:
                solution_coverage.complete_rows(caller_env, tasks._name, domain)
            self.assertNotIn(hidden_name, str(error.exception))

    def test_collection_query_budget_does_not_grow_per_task(self):
        tasks = (
            self.env["project.task"]
            .with_user(self.manager)
            .create(
                [
                    {
                        "name": f"SYNTHETIC query budget {index}",
                        "project_id": self.project.id,
                        "agile_item_type_id": self.env.ref(
                            "project_agile.project_agile_item_type_story"
                        ).id,
                    }
                    for index in range(12)
                ]
            )
        )
        caller = tasks.with_user(self.user)
        caller.check_access("read")  # Warm ordinary access metadata, not result rows.
        self.env.flush_all()
        before = self.cr.sql_log_count
        rows = solution_coverage.complete_rows(
            caller.env, caller._name, [("id", "in", tasks.ids)]
        )
        queries = self.cr.sql_log_count - before
        self.assertEqual(rows, tasks)
        self.assertLessEqual(
            queries,
            20,
            f"Bounded collection issued {queries} queries for 12 native Tasks",
        )
        _logger.info("M8_QUERY_BUDGET_OK native_tasks=12 queries=%s limit=20", queries)

    def test_same_company_visible_project_does_not_authorize_foreign_links(self):
        other_project = self._project(
            "Second readable initiative", "M8HARDOTHER", self.company
        )
        other_task = self._spike(project=other_project, item_type="story")
        requirement = self._requirement()
        other_task.with_user(self.manager).check_access("write")
        self.assertEqual(other_task.company_id, requirement.company_id)
        before = self.env["project.agile.requirement.task.link"].search_count([])
        with self.assertRaises(ValidationError):
            self.env["project.agile.requirement.task.link"].with_user(
                self.manager
            ).with_context(solution_trusted=True, skip_company_check=True).create(
                {"task_id": other_task.id, "requirement_revision_id": requirement.id}
            )
        self.assertEqual(
            self.env["project.agile.requirement.task.link"].search_count([]), before
        )
        self.assertFalse(requirement.sealed)

    def test_multi_enabled_company_manager_cannot_render_wrong_active_scope(self):
        baseline, requirement = self._approved()
        event = self._event(baseline, requirement)
        both = (self.company | self.other_company).ids
        baseline.with_context(allowed_company_ids=both).action_projection("customer")
        restricted = baseline.with_context(
            allowed_company_ids=self.other_company.ids,
            force_company=self.company.id,
            solution_trusted=True,
            sudo=True,
        )
        for action in (
            lambda: restricted.action_projection("customer"),
            restricted.action_coverage,
            lambda: restricted.read(["snapshot_json"]),
            lambda: restricted.export_data(["snapshot_json"]),
            lambda: event.with_env(restricted.env).export_data(["evidence"]),
        ):
            with self.assertRaises(AccessError):
                action()
        self.assertEqual(baseline.state, "approved")
        self.assertEqual(event.recorded_by_id, self.manager)

    def test_revoked_current_approver_cannot_accept_or_confirm_cached_intent(self):
        baseline, requirement = self._approved()
        intent = (
            self.env["project.agile.solution.task.intent"]
            .with_user(self.manager)
            .create(
                {
                    "name": "SYNTHETIC revoked confirmation",
                    "solution_id": self.solution.id,
                    "operation": "create",
                    "agile_item_type_id": self.env.ref(
                        "project_agile.project_agile_item_type_story"
                    ).id,
                    "requirement_revision_ids": [Command.set(requirement.ids)],
                    "document_revision_id": baseline.id,
                }
            )
        )
        intent.read(["name", "preview_text"])
        self._hide("project.project", self.project)
        count = self.env["project.task"].search_count([])
        with self.assertRaises(AccessError):
            self._event(baseline, requirement)
        with self.assertRaises(AccessError):
            intent.with_context(
                solution_trusted=True, default_state="consumed"
            ).action_confirm()
        self.assertEqual(self.env["project.task"].search_count([]), count)
        self.assertFalse(
            self.env["project.agile.requirement.acceptance"].search(
                [("document_revision_id", "=", baseline.id)]
            )
        )
        self.assertEqual(intent.sudo().state, "preview")

    def test_batch_link_failure_rolls_back_first_edge_and_content_seal(self):
        requirement, task = self._requirement(), self._spike(item_type="story")
        links = self.env["project.agile.requirement.task.link"].with_user(self.manager)
        with self.assertRaises(ValidationError):
            links.create(
                [
                    {"task_id": task.id, "requirement_revision_id": requirement.id},
                    {"task_id": True, "requirement_revision_id": requirement.id},
                ]
            )
        self.assertFalse(links.search([("task_id", "=", task.id)]))
        self.assertFalse(requirement.sealed)

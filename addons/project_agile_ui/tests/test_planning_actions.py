"""Regression coverage for authoritative Agile planning mutations."""

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


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
        self.first_task = self._create_task(
            "First Product Backlog item", agile_backlog_sequence=10
        )
        self.second_task = self._create_task(
            "Second Product Backlog item", agile_backlog_sequence=20
        )
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
        return (
            self.env["project.project"]
            .with_user(self.planner)
            .get_agile_planning_snapshot(self.project.id)
        )

    def _change(
        self,
        operation,
        task_ids,
        *,
        sprint_id=False,
        before_task_id=False,
        versions=None,
    ):
        expected_versions = versions or {}
        if expected_versions and set(expected_versions) != {"tasks", "sprints"}:
            task_version_ids = set(task_ids)
            if before_task_id:
                task_version_ids.add(before_task_id)
            sprint_version_ids = (
                {sprint_id}
                if sprint_id
                else set(
                    self.env["project.task"].browse(task_ids).mapped("sprint_id").ids
                )
            )
            expected_versions = {
                "tasks": {
                    str(record_id): expected_versions[record_id]
                    for record_id in task_version_ids
                    if record_id in expected_versions
                },
                "sprints": {
                    str(record_id): expected_versions[record_id]
                    for record_id in sprint_version_ids
                    if record_id in expected_versions
                },
            }
        return (
            self.env["project.project"]
            .with_user(self.planner)
            .apply_agile_planning_change(
                self.project.id,
                operation,
                task_ids,
                sprint_id=sprint_id,
                before_task_id=before_task_id,
                expected_versions=expected_versions,
            )
        )

    @staticmethod
    def _backlog_item(snapshot, task):
        return next(
            item for item in snapshot["backlog"]["items"] if item["id"] == task.id
        )

    @staticmethod
    def _sprint_item(snapshot, sprint):
        return next(item for item in snapshot["sprints"] if item["id"] == sprint.id)

    def test_planning_row_locks_accept_empty_recordsets_without_a_query(self):
        for model in ("project.sprint", "project.task"):
            with self.subTest(model=model):
                records = self.env[model]
                query_count = self.cr.sql_log_count

                self.project._lock_agile_planning_records(records)

                self.assertEqual(self.cr.sql_log_count, query_count)

    def test_planning_row_locks_reject_missing_records(self):
        for records in (self.sprint, self.first_task | self.second_task):
            with self.subTest(model=records._name):
                records[0].unlink()

                with self.assertRaisesRegex(
                    ValidationError, "A selected planning record no longer exists"
                ):
                    self.project._lock_agile_planning_records(records)

    def test_assigns_current_backlog_items_to_a_compatible_draft_sprint(self):
        snapshot = self._snapshot()
        task = self._backlog_item(snapshot, self.first_task)
        sprint = self._sprint_item(snapshot, self.sprint)

        updated = self._change(
            "assign",
            [self.first_task.id],
            sprint_id=self.sprint.id,
            versions={
                self.first_task.id: task["version"],
                self.sprint.id: sprint["version"],
            },
        )

        self.assertEqual(self.first_task.sprint_id, self.sprint)
        sprint_data = self._sprint_item(updated, self.sprint)
        self.assertEqual(
            [item["id"] for item in sprint_data["items"]], [self.first_task.id]
        )
        self.assertNotIn(
            self.first_task.id, [item["id"] for item in updated["backlog"]["items"]]
        )

    def test_assigns_when_task_and_sprint_ids_collide_in_separate_version_namespaces(
        self,
    ):
        """Task and Sprint optimistic tokens must not alias on equal numeric IDs."""
        task = self._create_task("Colliding Product Backlog item")
        sprint = self.sprint
        while task.id < sprint.id:
            task = self._create_task("Colliding Product Backlog item")
        while sprint.id < task.id:
            sprint = self.env["project.sprint"].create(
                {
                    "name": "Colliding Sprint",
                    "project_id": self.project.id,
                    "team_id": self.team.id,
                }
            )
        self.assertEqual(task.id, sprint.id)
        snapshot = self._snapshot()

        self._change(
            "assign",
            [task.id],
            sprint_id=sprint.id,
            versions={
                "tasks": {str(task.id): self._backlog_item(snapshot, task)["version"]},
                "sprints": {
                    str(sprint.id): self._sprint_item(snapshot, sprint)["version"]
                },
            },
        )

        self.assertEqual(task.sprint_id, sprint)

    def test_assigns_multiple_current_backlog_items_atomically(self):
        snapshot = self._snapshot()
        versions = {
            self.first_task.id: self._backlog_item(snapshot, self.first_task)[
                "version"
            ],
            self.second_task.id: self._backlog_item(snapshot, self.second_task)[
                "version"
            ],
            self.sprint.id: self._sprint_item(snapshot, self.sprint)["version"],
        }

        self._change(
            "assign",
            [self.first_task.id, self.second_task.id],
            sprint_id=self.sprint.id,
            versions=versions,
        )

        self.assertEqual(self.first_task.sprint_id, self.sprint)
        self.assertEqual(self.second_task.sprint_id, self.sprint)

    def test_rejects_active_sprint_assignment_without_partial_write(self):
        self.sprint.action_start()
        snapshot = self._snapshot()
        task = self._backlog_item(snapshot, self.first_task)
        sprint = self._sprint_item(snapshot, self.sprint)

        with self.assertRaises(ValidationError):
            self._change(
                "assign",
                [self.first_task.id],
                sprint_id=self.sprint.id,
                versions={
                    self.first_task.id: task["version"],
                    self.sprint.id: sprint["version"],
                },
            )

        self.assertFalse(self.first_task.sprint_id)
        self.assertFalse(self.sprint.scope_event_ids)

    def test_rejects_multi_assignment_with_an_ineligible_item_without_partial_write(
        self,
    ):
        ineligible_type = self.env["project.agile.item.type"].create(
            {
                "name": "Interactive Chore",
                "code": "interactive_chore",
                "can_schedule_in_sprint": False,
            }
        )
        ineligible_task = self.env["project.task"].create(
            {
                "name": "Ineligible Product Backlog item",
                "project_id": self.project.id,
                "agile_item_type_id": ineligible_type.id,
            }
        )
        snapshot = self._snapshot()
        versions = {
            self.first_task.id: self._backlog_item(snapshot, self.first_task)[
                "version"
            ],
            ineligible_task.id: self.env[
                "project.project"
            ]._agile_planning_record_version(ineligible_task),
            self.sprint.id: self._sprint_item(snapshot, self.sprint)["version"],
        }

        with self.assertRaises(ValidationError):
            self._change(
                "assign",
                [self.first_task.id, ineligible_task.id],
                sprint_id=self.sprint.id,
                versions=versions,
            )

        self.assertFalse(self.first_task.sprint_id)
        self.assertFalse(ineligible_task.sprint_id)
        self.assertFalse(self.sprint.scope_event_ids)

    def test_rejects_stale_assignment_without_partial_write(self):
        snapshot = self._snapshot()
        task = self._backlog_item(snapshot, self.first_task)
        sprint = self._sprint_item(snapshot, self.sprint)
        self.first_task.write({"name": "Changed after snapshot"})

        with self.assertRaises(ValidationError):
            self._change(
                "assign",
                [self.first_task.id],
                sprint_id=self.sprint.id,
                versions={
                    self.first_task.id: task["version"],
                    self.sprint.id: sprint["version"],
                },
            )

        self.assertFalse(self.first_task.sprint_id)

    def test_rejects_duplicate_assignment_retry_without_partial_state(self):
        snapshot = self._snapshot()
        versions = {
            self.first_task.id: self._backlog_item(snapshot, self.first_task)[
                "version"
            ],
            self.sprint.id: self._sprint_item(snapshot, self.sprint)["version"],
        }
        self._change(
            "assign", [self.first_task.id], sprint_id=self.sprint.id, versions=versions
        )

        with self.assertRaises(ValidationError):
            self._change(
                "assign",
                [self.first_task.id],
                sprint_id=self.sprint.id,
                versions=versions,
            )

        self.assertEqual(self.first_task.sprint_id, self.sprint)
        self.assertFalse(self.sprint.scope_event_ids)

    def test_reorders_the_current_backlog_under_server_preconditions(self):
        snapshot = self._snapshot()
        first = self._backlog_item(snapshot, self.first_task)
        second = self._backlog_item(snapshot, self.second_task)

        updated = self._change(
            "reorder",
            [self.second_task.id],
            before_task_id=self.first_task.id,
            versions={
                self.second_task.id: second["version"],
                self.first_task.id: first["version"],
            },
        )

        self.assertEqual(
            [item["id"] for item in updated["backlog"]["items"][:2]],
            [self.second_task.id, self.first_task.id],
        )
        self.assertLess(
            self.second_task.agile_backlog_sequence,
            self.first_task.agile_backlog_sequence,
        )

    def test_rejects_a_stale_reorder_without_changing_the_current_order(self):
        snapshot = self._snapshot()
        first = self._backlog_item(snapshot, self.first_task)
        second = self._backlog_item(snapshot, self.second_task)
        self.first_task.write({"agile_backlog_sequence": 30})
        original_sequences = {
            self.first_task.id: self.first_task.agile_backlog_sequence,
            self.second_task.id: self.second_task.agile_backlog_sequence,
        }

        with self.assertRaises(ValidationError):
            self._change(
                "reorder",
                [self.second_task.id],
                before_task_id=self.first_task.id,
                versions={
                    self.second_task.id: second["version"],
                    self.first_task.id: first["version"],
                },
            )

        self.assertEqual(
            self.first_task.agile_backlog_sequence,
            original_sequences[self.first_task.id],
        )
        self.assertEqual(
            self.second_task.agile_backlog_sequence,
            original_sequences[self.second_task.id],
        )

    def test_reorder_updates_a_bounded_neighbor_set_for_a_large_backlog(self):
        """A single reorder must not lock or rewrite every backlog row."""
        for index in range(250):
            self._create_task(
                f"Large backlog item {index}", agile_backlog_sequence=(index + 3) * 10
            )
        snapshot = self._snapshot()
        first = self._backlog_item(snapshot, self.first_task)
        second = self._backlog_item(snapshot, self.second_task)
        query_count = self.cr.sql_log_count

        self._change(
            "reorder",
            [self.second_task.id],
            before_task_id=self.first_task.id,
            versions={
                "tasks": {
                    str(self.second_task.id): second["version"],
                    str(self.first_task.id): first["version"],
                },
                "sprints": {},
            },
        )

        self.assertLess(self.cr.sql_log_count - query_count, 60)
        self.assertLess(
            self.second_task.agile_backlog_sequence,
            self.first_task.agile_backlog_sequence,
        )

    def test_active_sprint_return_appends_scope_history_through_the_shared_task_path(
        self,
    ):
        self.first_task.assign_product_backlog_to_sprint(self.sprint)
        self.sprint.action_start()
        snapshot = self._snapshot()
        task = next(
            item
            for item in self._sprint_item(snapshot, self.sprint)["items"]
            if item["id"] == self.first_task.id
        )
        sprint = self._sprint_item(snapshot, self.sprint)
        events_before = len(self.sprint.scope_event_ids)

        self._change(
            "return",
            [self.first_task.id],
            versions={
                self.first_task.id: task["version"],
                self.sprint.id: sprint["version"],
            },
        )

        self.assertFalse(self.first_task.sprint_id)
        self.assertEqual(len(self.sprint.scope_event_ids), events_before + 1)
        self.assertEqual(self.sprint.scope_event_ids[-1].event_type, "removed")

    def test_rejects_return_from_a_closed_sprint_without_erasing_history(self):
        self.first_task.assign_product_backlog_to_sprint(self.sprint)
        self.sprint._set_lifecycle_state("closed")
        task_version = self.env["project.project"]._agile_planning_record_version(
            self.first_task
        )
        sprint_version = self.env["project.project"]._agile_planning_record_version(
            self.sprint
        )

        with self.assertRaises(ValidationError):
            self._change(
                "return",
                [self.first_task.id],
                versions={
                    self.first_task.id: task_version,
                    self.sprint.id: sprint_version,
                },
            )

        self.assertEqual(self.first_task.sprint_id, self.sprint)
        self.assertFalse(self.sprint.scope_event_ids)

    def test_rejects_an_accessible_sprint_from_another_project_before_assignment(self):
        other_project = self.env["project.project"].create(
            {
                "name": "Other Planning Project",
                "privacy_visibility": "employees",
                "company_id": self.env.company.id,
                "agile_enabled": True,
                "agile_key": "OTHER",
            }
        )
        other_team = self.env["project.agile.team"].create(
            {"name": "Other Planning Team", "project_id": other_project.id}
        )
        other_sprint = self.env["project.sprint"].create(
            {
                "name": "Other Sprint",
                "project_id": other_project.id,
                "team_id": other_team.id,
            }
        )
        snapshot = self._snapshot()

        with self.assertRaises(AccessError):
            self._change(
                "assign",
                [self.first_task.id],
                sprint_id=other_sprint.id,
                versions={
                    self.first_task.id: self._backlog_item(snapshot, self.first_task)[
                        "version"
                    ]
                },
            )

        self.assertFalse(self.first_task.sprint_id)

    def test_non_manager_with_enabled_multi_company_access_uses_current_company_scope(
        self,
    ):
        other_company = self.env["res.company"].create(
            {"name": "Planning Secondary Company"}
        )
        planner = mail_new_test_user(
            self.env, "Multi-company project user", groups="project.group_project_user"
        )
        planner.company_ids = [(6, 0, (self.env.company | other_company).ids)]
        planner_env = (
            self.env["project.project"]
            .with_user(planner)
            .with_context(allowed_company_ids=(self.env.company | other_company).ids)
        )
        snapshot = planner_env.get_agile_planning_snapshot(self.project.id)
        task = self._backlog_item(snapshot, self.first_task)
        sprint = self._sprint_item(snapshot, self.sprint)

        updated = planner_env.apply_agile_planning_change(
            self.project.id,
            "assign",
            [self.first_task.id],
            sprint_id=self.sprint.id,
            expected_versions={
                "tasks": {str(self.first_task.id): task["version"]},
                "sprints": {str(self.sprint.id): sprint["version"]},
            },
        )

        self.assertNotIn(
            self.first_task.id, [item["id"] for item in updated["backlog"]["items"]]
        )
        self.assertEqual(self.first_task.sprint_id, self.sprint)

    def test_rejects_an_inaccessible_project_before_disclosing_or_mutating_tasks(self):
        private_project = self.env["project.project"].create(
            {
                "name": "Private Planning Project",
                "privacy_visibility": "followers",
                "company_id": self.env.company.id,
                "agile_enabled": True,
                "agile_key": "PRIVATE",
            }
        )
        private_team = self.env["project.agile.team"].create(
            {"name": "Private Planning Team", "project_id": private_project.id}
        )
        private_sprint = self.env["project.sprint"].create(
            {
                "name": "Private Sprint",
                "project_id": private_project.id,
                "team_id": private_team.id,
            }
        )
        private_task = self.env["project.task"].create(
            {
                "name": "Private backlog item",
                "project_id": private_project.id,
                "agile_item_type_id": self.eligible_type.id,
            }
        )
        outsider = mail_new_test_user(
            self.env,
            "Planning unauthorized outsider",
            groups="project.group_project_user",
        )

        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(outsider).apply_agile_planning_change(
                private_project.id,
                "assign",
                [private_task.id],
                sprint_id=private_sprint.id,
                expected_versions={},
            )

        self.assertFalse(private_task.sprint_id)

    def test_rejects_unreadable_selected_tasks_before_any_mutation(self):
        other_company = self.env["res.company"].create(
            {"name": "Unrelated Planning Company"}
        )
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
            self._change(
                "assign", [self.first_task.id, other_task.id], sprint_id=self.sprint.id
            )

        self.assertFalse(self.first_task.sprint_id)

    def test_rejects_version_payloads_without_exact_model_namespaces(self):
        snapshot = self._snapshot()
        task = self._backlog_item(snapshot, self.first_task)
        sprint = self._sprint_item(snapshot, self.sprint)

        with self.assertRaises(ValidationError):
            self.env["project.project"].with_user(
                self.planner
            ).apply_agile_planning_change(
                self.project.id,
                "assign",
                [self.first_task.id],
                sprint_id=self.sprint.id,
                expected_versions={
                    self.first_task.id: task["version"],
                    self.sprint.id: sprint["version"],
                },
            )

        self.assertFalse(self.first_task.sprint_id)

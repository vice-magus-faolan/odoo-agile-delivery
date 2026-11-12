"""Regression coverage for the read-only Agile planning snapshot boundary."""

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, warmup

from odoo.addons.mail.tests.common import mail_new_test_user


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
        self.backlog_task = self._create_task(
            "Product Backlog work", agile_story_points=5
        )

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
            item
            for item in snapshot["backlog"]["items"]
            if item["id"] == self.backlog_task.id
        )
        self.assertEqual(backlog_item["agile_key"], self.backlog_task.agile_key)
        self.assertEqual(backlog_item["story_points"], 5)
        self.assertEqual(backlog_item["item_type"], self.eligible_type.display_name)
        self.assertIsNone(backlog_item["parent"])

    def test_committed_points_follow_current_sprint_not_loaded_window(self):
        first = self._create_sprint("Original commitment")
        second = self._create_sprint("Destination draft")
        moved = self._create_task("Moved X", agile_story_points=5)
        retained = self._create_task("Retained Y", agile_story_points=3)
        planner = mail_new_test_user(
            self.env, "Moving planner", groups="project.group_project_manager"
        )
        (moved | retained).with_user(planner).assign_product_backlog_to_sprint(first)
        first.with_user(planner).action_start()
        events = first.scope_event_ids
        event_fields = [
            "sprint_id",
            "task_id",
            "event_type",
            "story_points",
            "previous_story_points",
            "actor_id",
            "event_at",
            "reason",
            "carryover_target_sprint_id",
        ]
        history = events.read(event_fields, load=None)
        committed_ids = first.committed_task_ids.ids
        reader = mail_new_test_user(
            self.env, "Moved work reader", groups="project.group_project_user"
        )
        model = self.env["project.project"].with_user(reader)
        before = model.get_agile_planning_snapshot(self.project.id)
        original = next(row for row in before["sprints"] if row["id"] == first.id)
        self.assertEqual(
            (original["current_points"], original["committed_points"]), (8, 8)
        )

        moved.with_user(planner).return_sprint_tasks_to_product_backlog()
        moved.with_user(planner).assign_product_backlog_to_sprint(
            second, draft_only=True
        )
        self.assertEqual(moved.sprint_id, second)
        self.assertEqual(retained.sprint_id, first)
        totals = []
        for destination_visible in (True, False):
            if not destination_visible:
                for index in range(20):
                    self._create_sprint(f"Newer draft {index}")
            self.env.flush_all()
            self.env.invalidate_all()
            page = model.get_agile_planning_snapshot(self.project.id)
            rows = {row["id"]: row for row in page["sprints"]}
            self.assertEqual(second.id in rows, destination_visible)
            original = rows[first.id]
            self.assertEqual([item["id"] for item in original["items"]], retained.ids)
            totals.append((original["current_points"], original["committed_points"]))
            self.assertEqual(events.read(event_fields, load=None), history)
            self.assertEqual(first.committed_task_ids.ids, committed_ids)
            self.assertEqual(
                first.scope_event_ids.filtered(
                    lambda event: event.event_type == "committed"
                ),
                events,
            )
        self.assertEqual(totals, [(3, 3), (3, 3)])

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

    def test_team_filter_pages_and_fallback_exclude_closed_and_foreign_work(self):
        second_team = self.env["project.agile.team"].create(
            {"name": "BA Team", "project_id": self.project.id}
        )
        chosen = self._create_sprint()
        self._create_sprint("BA Sprint", team=second_team)
        expected = self.env["project.task"]
        for index in range(51):
            expected |= self._create_task(f"Dev {index}", agile_team_id=self.team.id)
            self._create_task(f"BA {index}", agile_team_id=second_team.id)
        self._create_task("Done", agile_team_id=self.team.id, state="1_done")
        self._create_task("Canceled", agile_team_id=self.team.id, state="1_canceled")
        for item_type_id in (self.ineligible_type.id, False):
            self._create_task(
                "Not Sprint-eligible",
                agile_item_type_id=item_type_id,
                agile_team_id=self.team.id,
            )
        self._create_task(
            "Template",
            is_template=True,
            agile_item_type_id=False,
            agile_team_id=self.team.id,
        )
        user = mail_new_test_user(
            self.env, "Team snapshot planner", groups="project.group_project_user"
        )
        model = self.env["project.project"].with_user(user)
        first = model.get_agile_planning_snapshot(self.project.id, team_id=self.team.id)
        cursor = first["backlog"]["next_cursor"]
        second = model.get_agile_planning_snapshot(
            self.project.id, cursor, team_id=self.team.id
        )
        self.assertEqual(len(first["backlog"]["items"]), 50)
        self.assertEqual(len(second["backlog"]["items"]), 1)
        self.assertEqual(
            {
                row["id"]
                for row in first["backlog"]["items"] + second["backlog"]["items"]
            },
            set(expected.ids),
        )
        self.assertEqual([row["id"] for row in first["sprints"]], chosen.ids)
        self.assertEqual(
            {row["id"] for row in first["teams"]}, {self.team.id, second_team.id}
        )
        action = self.project.with_user(user).action_open_agile_planning_backlog(
            team_id=self.team.id
        )
        self.assertEqual(
            set(self.env["project.task"].with_user(user).search(action["domain"]).ids),
            set(expected.ids),
        )
        for team_id in (False, second_team.id):
            with self.assertRaises(ValidationError):
                model.get_agile_planning_snapshot(
                    self.project.id, cursor, team_id=team_id
                )
        with self.assertRaises(ValidationError):
            model.get_agile_planning_snapshot(self.project.id, team_id=True)
        self.team.active = False
        with self.assertRaises(AccessError):
            model.get_agile_planning_snapshot(self.project.id, team_id=self.team.id)

    def test_team_selection_cannot_resolve_a_team_from_another_project(self):
        other = self.env["project.project"].create(
            {
                "name": "Private team project",
                "privacy_visibility": "followers",
                "agile_enabled": True,
                "agile_key": "HIDDENTEAM",
            }
        )
        team = self.env["project.agile.team"].create(
            {"name": "Hidden team", "project_id": other.id}
        )
        user = mail_new_test_user(
            self.env, "Team outsider", groups="project.group_project_user"
        )
        model = self.env["project.project"].with_user(user)
        with self.assertRaises(AccessError):
            model.get_agile_planning_snapshot(self.project.id, team_id=team.id)
        self.assertNotIn(
            team.id,
            [
                row["id"]
                for row in model.get_agile_planning_snapshot(self.project.id)["teams"]
            ],
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
        other_company = self.env["res.company"].create(
            {"name": "Other Planning Company"}
        )
        user = mail_new_test_user(
            self.env, "Multi-company planner", groups="project.group_project_user"
        )
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

    def test_snapshot_rejects_a_cursor_after_a_planning_reorder(self):
        for index in range(51):
            self._create_task(
                f"Cursor backlog item {index}", agile_backlog_sequence=(index + 2) * 10
            )
        first_page = self._snapshot()
        moved = first_page["backlog"]["items"][0]

        self.env["project.project"].apply_agile_planning_change(
            self.project.id,
            "reorder",
            [moved["id"]],
            before_task_id=False,
            expected_versions={
                "tasks": {str(moved["id"]): moved["version"]},
                "sprints": {},
            },
        )

        with self.assertRaises(ValidationError):
            self._snapshot(first_page["backlog"]["next_cursor"])

    @warmup
    def test_snapshot_keeps_the_documented_query_and_payload_budget(self):
        """Bound representative reads so larger boards cannot become
        card-by-card queries.
        """
        for index in range(3):
            sprint = self._create_sprint(f"Budget Sprint {index}")
            self._create_task(f"Sprint budget item {index}", sprint_id=sprint.id)
        for index in range(50):
            self._create_task(f"Backlog budget item {index}")

        query_count = self.cr.sql_log_count
        snapshot = self._snapshot()
        query_count = self.cr.sql_log_count - query_count

        self.assertLessEqual(query_count, 10)
        self.assertEqual(len(snapshot["sprints"]), 3)
        self.assertEqual(sum(len(sprint["items"]) for sprint in snapshot["sprints"]), 3)
        self.assertEqual(len(snapshot["backlog"]["items"]), 50)
        self.assertTrue(snapshot["backlog"]["next_cursor"])

    def test_query_budget_with_more_teams_and_persisted_cards(self):
        """Creation caches must not hide per-team or per-card serialization reads."""
        for index in range(8):
            team = self.env["project.agile.team"].create(
                {"name": f"Budget Team {index}", "project_id": self.project.id}
            )
            sprint = self._create_sprint(f"Team Budget Sprint {index}", team=team)
            for card in range(10):
                self._create_task(f"Team {index} card {card}", sprint_id=sprint.id)
        for index in range(80):
            self._create_task(f"Large backlog item {index}")
        self.env.flush_all()
        self.env.invalidate_all()

        query_count = self.cr.sql_log_count
        snapshot = self._snapshot()
        query_count = self.cr.sql_log_count - query_count

        self.assertLessEqual(query_count, 10)
        self.assertEqual(len(snapshot["teams"]), 9)
        self.assertEqual(len(snapshot["sprints"]), 8)
        self.assertEqual(
            sum(len(sprint["items"]) for sprint in snapshot["sprints"]), 80
        )
        self.assertEqual(len(snapshot["backlog"]["items"]), 50)
        self.assertTrue(snapshot["backlog"]["next_cursor"])

    def test_planning_action_is_project_scoped_and_read_only(self):
        action = self.project.action_open_agile_planning()

        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "project_agile_ui.planning")
        self.assertEqual(action["context"], {"project_id": self.project.id})

    def test_all_windows_are_reachable_with_cold_bounded_pages(self):
        teams = (
            self.env["project.agile.team"].create(
                [
                    {"name": f"Page team {i}", "project_id": self.project.id}
                    for i in range(105)
                ]
            )
            | self.team
        )
        sprints = self.env["project.sprint"].create(
            [
                {
                    "name": f"Page Sprint {i}",
                    "project_id": self.project.id,
                    "team_id": self.team.id,
                }
                for i in range(23)
            ]
        )
        tasks = self.env["project.task"].create(
            [
                {
                    "name": f"Page assigned {i}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.eligible_type.id,
                    "sprint_id": sprints[-1].id if i < 205 else sprints[0].id,
                    "agile_backlog_sequence": i // 3,
                }
                for i in range(310)
            ]
        )
        backlog = (
            self.env["project.task"].create(
                [
                    {
                        "name": f"Page backlog {i}",
                        "project_id": self.project.id,
                        "agile_item_type_id": self.eligible_type.id,
                    }
                    for i in range(105)
                ]
            )
            | self.backlog_task
        )
        user = mail_new_test_user(
            self.env, "Page planner", groups="project.group_project_user"
        )
        model = self.env["project.project"].with_user(user)
        model.get_agile_planning_snapshot(self.project.id)
        options, seen_sprints, seen_tasks = {}, [], []
        while True:
            self.env.flush_all()
            self.env.invalidate_all()
            count = self.cr.sql_log_count
            page = model.get_agile_planning_snapshot(self.project.id, **options)
            self.assertLessEqual(self.cr.sql_log_count - count, 12)
            self.assertLessEqual(len(page["sprints"]), 20)
            rows = page["sprints"]
            seen_sprints.extend(row["id"] for row in rows)
            while True:
                self.assertLessEqual(sum(len(row["items"]) for row in rows), 100)
                seen_tasks.extend(item["id"] for row in rows for item in row["items"])
                for row in rows:
                    self.assertEqual(
                        row["item_count"],
                        205
                        if row["id"] == sprints[-1].id
                        else 105
                        if row["id"] == sprints[0].id
                        else 0,
                    )
                if not page["pages"]["tasks"]:
                    break
                self.env.invalidate_all()
                count = self.cr.sql_log_count
                page = model.get_agile_planning_snapshot(
                    self.project.id, **options, task_cursor=page["pages"]["tasks"]
                )
                self.assertLessEqual(self.cr.sql_log_count - count, 12)
                rows = page["sprints"]
            if not page["pages"]["sprints"]:
                break
            options = {"sprint_cursor": page["pages"]["sprints"]}
        first = model.get_agile_planning_snapshot(self.project.id)
        second = model.get_agile_planning_snapshot(
            self.project.id, sprint_cursor=first["pages"]["sprints"]
        )
        self.env.invalidate_all()
        count = self.cr.sql_log_count
        combined = model.get_agile_planning_snapshot(
            self.project.id,
            sprint_cursor=first["pages"]["sprints"],
            task_cursor=second["pages"]["tasks"],
            team_cursor=first["pages"]["teams"],
        )
        self.assertLessEqual(self.cr.sql_log_count - count, 13)
        self.assertEqual(sum(len(row["items"]) for row in combined["sprints"]), 5)
        with self.assertRaises(ValidationError):
            model.get_agile_planning_snapshot(
                self.project.id, task_cursor=second["pages"]["tasks"]
            )
        self.assertEqual(seen_sprints, list(reversed(sprints.ids)))
        self.assertEqual(len(seen_tasks), len(set(seen_tasks)))
        self.assertEqual(set(seen_tasks), set(tasks.ids))
        seen_teams, cursor = [], False
        while True:
            page = model.get_agile_planning_snapshot(
                self.project.id, team_cursor=cursor
            )
            seen_teams.extend(row["id"] for row in page["teams"])
            cursor = page["pages"]["teams"]
            if not cursor:
                break
        self.assertEqual(seen_teams, sorted(teams.ids))
        seen_backlog, cursor = [], False
        while True:
            page = model.get_agile_planning_snapshot(self.project.id, cursor)
            seen_backlog.extend(row["id"] for row in page["backlog"]["items"])
            cursor = page["backlog"]["next_cursor"]
            if not cursor:
                break
        self.assertEqual(seen_backlog, sorted(backlog.ids))

    def test_page_tokens_bind_scope_anchor_and_planning_revision(self):
        sprints = self.env["project.sprint"].create(
            [
                {
                    "name": f"Token Sprint {i}",
                    "project_id": self.project.id,
                    "team_id": self.team.id,
                }
                for i in range(21)
            ]
        )
        first = self._snapshot()
        token = first["pages"]["sprints"]
        model = self.env["project.project"]
        for cursor in (True, {}, {**token, "id": True}, {**token, "version": "old"}):
            with self.assertRaises(ValidationError):
                model.get_agile_planning_snapshot(self.project.id, sprint_cursor=cursor)
        with self.assertRaises(ValidationError):
            model.get_agile_planning_snapshot(
                self.project.id, team_id=self.team.id, sprint_cursor=token
            )
        with self.assertRaises(ValidationError):
            model.get_agile_planning_snapshot(self.project.id, team_cursor=token)
        anchor = sprints.browse(token["id"])
        anchor.name = "Changed page anchor"
        self.env.flush_all()
        # write_date has transaction-clock resolution; use the versioned planning
        # revision to exercise a guaranteed cross-page invalidation as well.
        self.project.agile_planning_backlog_revision += 1
        with self.assertRaises(ValidationError):
            model.get_agile_planning_snapshot(self.project.id, sprint_cursor=token)

    def test_page_anchor_must_belong_to_current_domain(self):
        first = self._create_sprint("In-scope anchor")
        other_team = self.env["project.agile.team"].create(
            {"name": "Other accessible team", "project_id": self.project.id}
        )
        outside = self._create_sprint("Outside team filter", team=other_team)
        user = mail_new_test_user(
            self.env, "Anchor scope reader", groups="project.group_project_user"
        )
        self.env.flush_all()
        model = self.env["project.project"].with_user(user)
        outside.with_user(user).check_access("read")
        scope = {
            "project": self.project.id,
            "team": self.team.id,
            "milestone": False,
            "revision": self.project.agile_planning_backlog_revision,
            "page": "sprints",
        }
        valid = {"id": first.id, "version": str(first.write_date), "scope": scope}
        accepted = model.get_agile_planning_snapshot(
            self.project.id, team_id=self.team.id, sprint_cursor=valid
        )
        self.assertFalse(accepted["sprints"])
        for anchor in (outside, first):
            if anchor == first:
                first.with_user(self.env.user).action_start()
                first.with_user(self.env.user)._close_with_disposition(
                    "product_backlog"
                )
            token = {"id": anchor.id, "version": str(anchor.write_date), "scope": scope}
            with self.assertRaisesRegex(
                ValidationError, "The planning page changed. Refresh and retry."
            ):
                model.get_agile_planning_snapshot(
                    self.project.id, team_id=self.team.id, sprint_cursor=token
                )
        page = model.get_agile_planning_snapshot(self.project.id)
        self.assertEqual([row["id"] for row in page["sprints"]], outside.ids)

    def test_filtered_counts_and_points_exclude_hidden_assigned_work(self):
        self.project.allow_milestones = True
        milestone = self.env["project.milestone"].create(
            {
                "name": "Scoped release",
                "project_id": self.project.id,
            }
        )
        sprint = self._create_sprint()
        visible = self.env["project.task"].create(
            [
                {
                    "name": f"Visible scoped work {i}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.eligible_type.id,
                    "sprint_id": sprint.id,
                    "milestone_id": milestone.id,
                    "agile_story_points": 3,
                }
                for i in range(101)
            ]
        )
        hidden = self._create_task(
            "Hidden scoped work",
            sprint_id=sprint.id,
            milestone_id=milestone.id,
            agile_story_points=8,
        )
        self._create_task(
            "Other release work", sprint_id=sprint.id, agile_story_points=5
        )
        sprint.action_start()
        user = mail_new_test_user(
            self.env,
            "Scoped page planner",
            groups="project.group_project_user,project.group_project_milestone",
        )
        self.env["ir.rule"].create(
            {
                "name": "Hide one planning task",
                "model_id": self.env["ir.model"]._get_id("project.task"),
                "domain_force": repr([("id", "!=", hidden.id)]),
            }
        )
        page = (
            self.env["project.project"]
            .with_user(user)
            .get_agile_planning_snapshot(self.project.id, milestone_id=milestone.id)
        )
        row = page["sprints"][0]
        self.assertEqual([item["id"] for item in row["items"]], visible[:100].ids)
        self.assertEqual(row["item_count"], 101)
        self.assertEqual(row["current_points"], 3 * 101)
        self.assertEqual(row["committed_points"], 3 * 101)
        cursor = page["pages"]["tasks"]
        model = self.env["project.project"].with_user(user)
        with self.assertRaises(ValidationError):
            model.get_agile_planning_snapshot(self.project.id, task_cursor=cursor)
        final = model.get_agile_planning_snapshot(
            self.project.id, milestone_id=milestone.id, task_cursor=cursor
        )["sprints"][0]
        self.assertEqual([item["id"] for item in final["items"]], visible[100:].ids)
        self.assertEqual(final["item_count"], 101)
        self.assertEqual(final["current_points"], 3 * 101)
        self.assertEqual(final["committed_points"], 3 * 101)

"""Real ORM and rendered Odoo journeys for the optional two-axis board."""

import json

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestAgileSwimlanes(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env, "swim_reader", groups="project_agile.group_agile_member"
        )
        cls.other_user = mail_new_test_user(
            cls.env, "swim_other", groups="project.group_project_user"
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Swimlane Project",
                "agile_enabled": True,
                "agile_key": "SWIM",
                "privacy_visibility": "employees",
                "company_id": cls.env.company.id,
            }
        )
        cls.teams = cls.env["project.agile.team"].create(
            [
                {"name": name, "project_id": cls.project.id}
                for name in ("Swim team", "Other swim team")
            ]
        )
        cls.sprints = cls.env["project.sprint"].create(
            [
                {"name": name, "project_id": cls.project.id, "team_id": team.id}
                for name, team in zip(
                    ("Swim Sprint", "Other swim Sprint"), cls.teams, strict=True
                )
            ]
        )
        cls.item_type = cls.env["project.agile.item.type"].create(
            {
                "name": "Swim Story",
                "code": "swim_story",
                "can_schedule_in_sprint": True,
            }
        )
        cls.item_type.allowed_child_type_ids = [Command.link(cls.item_type.id)]
        cls.epic_type = cls.env.ref("project_agile.project_agile_item_type_epic")
        cls.epic_type.allowed_child_type_ids = [Command.link(cls.item_type.id)]
        cls.stages = cls.env["project.task.type"].create(
            [
                {
                    "name": name,
                    "project_ids": [Command.link(cls.project.id)],
                    "agile_item_type_ids": [Command.link(cls.item_type.id)],
                    "sequence": sequence,
                }
                for name, sequence in (("Swim Todo", 1), ("Swim Doing", 2))
            ]
        )
        cls.epic = cls.env["project.task"].create(
            {
                "name": "Visible Epic",
                "project_id": cls.project.id,
                "agile_item_type_id": cls.epic_type.id,
            }
        )
        cls.parent = cls._task("Swim story", sprint_id=False, parent_id=cls.epic.id)
        cls.nested = cls._task(
            "Nested work",
            parent_id=cls.parent.id,
            stage_id=cls.stages[1].id,
            user_ids=[Command.set(cls.user.ids)],
        )
        cls.solo = cls._task("Solo work", user_ids=[Command.set(cls.user.ids)])
        cls.shared = cls._task(
            "Shared work", user_ids=[Command.set((cls.user | cls.other_user).ids)]
        )
        cls.unassigned = cls._task("Unassigned work", user_ids=[Command.clear()])
        cls.other = cls._task("Other team work", sprint_id=cls.sprints[1].id)
        cls.hidden = cls._task("Hidden swim work")
        cls.visible = cls.nested | cls.solo | cls.shared | cls.unassigned | cls.other
        cls.env["ir.rule"].create(
            {
                "name": "Hide swim fixture work",
                "model_id": cls.env["ir.model"]._get_id("project.task"),
                "domain_force": repr([("id", "!=", cls.hidden.id)]),
            }
        )
        cls.sprints.action_start()

    @classmethod
    def _task(cls, name, **values):
        return cls.env["project.task"].create(
            {
                "name": name,
                "project_id": cls.project.id,
                "agile_item_type_id": cls.item_type.id,
                "stage_id": cls.stages[0].id,
                "sprint_id": cls.sprints[0].id,
                **values,
            }
        )

    def _snapshot(self, **kwargs):
        return (
            self.env["project.project"]
            .with_user(self.user)
            .get_agile_swimlane_snapshot(self.project.id, **kwargs)
        )

    @staticmethod
    def _ids(snapshot):
        return {item["id"] for lane in snapshot["lanes"] for item in lane["items"]}

    def _history(self):
        return self.sprints.scope_event_ids.read(
            [
                "sprint_id",
                "task_id",
                "event_type",
                "story_points",
                "previous_story_points",
                "actor_id",
                "event_at",
                "reason",
                "carryover_target_sprint_id",
            ],
            load=None,
        )

    def _placement(self):
        """Snapshot native placement without imposing an assignee order."""
        rows = self.visible.read(
            ["parent_id", "user_ids", "sprint_id", "stage_id"], load=None
        )
        for row in rows:
            row["user_ids"] = sorted(row["user_ids"])
        return rows

    def test_nearest_epic_multi_owner_and_unique_totals_preserve_native_work(self):
        before = self._placement()
        history = self._history()
        epic = self._snapshot()
        self.assertEqual(epic["total"], len(self.visible))
        self.assertEqual(self._ids(epic), set(self.visible.ids))
        epic_lane = next(
            row for row in epic["lanes"] if row["id"] == f"epic:{self.epic.id}"
        )
        self.assertEqual([row["id"] for row in epic_lane["items"]], self.nested.ids)
        self.assertEqual({row["id"] for row in epic["stages"]}, set(self.stages.ids))
        owners = self._snapshot(grouping="assignee")
        multiple = next(row for row in owners["lanes"] if row["id"] == "multiple")
        self.assertEqual([row["id"] for row in multiple["items"]], self.shared.ids)
        self.assertIn("none", {row["id"] for row in owners["lanes"]})
        self.assertEqual(
            sum(len(row["items"]) for row in owners["lanes"]), owners["total"]
        )
        self.assertEqual(self._ids(owners), set(self.visible.ids))
        self.assertEqual(before, self._placement())
        self.assertEqual(history, self._history())

    def test_complete_navigation_and_matching_native_drilldowns(self):
        extra = self.env["project.task"].create(
            [
                {
                    "name": f"Paged swim {index}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.item_type.id,
                    "sprint_id": self.sprints[0].id,
                    "stage_id": self.stages[0].id,
                }
                for index in range(57)
            ]
        )
        expected = set((self.visible | extra).ids)
        seen, cursor = set(), False
        for _page in range(3):
            snapshot = self._snapshot(cursor=cursor)
            self.assertEqual(snapshot["total"], len(expected))
            self.assertLessEqual(snapshot["shown"], 50)
            self.assertLessEqual(len(snapshot["lanes"]), 50)
            self.assertFalse(seen & self._ids(snapshot))
            seen |= self._ids(snapshot)
            for lane in snapshot["lanes"]:
                ids = [row["id"] for row in lane["items"]]
                action = self.project.with_user(
                    self.user
                ).action_open_agile_swimlane_tasks(task_ids=ids)
                json.dumps(action)
                self.assertEqual(
                    set(
                        self.env["project.task"]
                        .with_user(self.user)
                        .search(action["domain"])
                        .ids
                    ),
                    set(ids),
                )
            cursor = snapshot["next_cursor"]
            if not cursor:
                break
        self.assertFalse(cursor)
        self.assertEqual(seen, expected)
        action = self.project.with_user(self.user).action_open_agile_swimlane_tasks()
        json.dumps(action)
        self.assertEqual(
            set(
                self.env["project.task"]
                .with_user(self.user)
                .search(action["domain"])
                .ids
            ),
            expected,
        )

    def test_filters_and_cursor_scope_are_authoritative(self):
        filtered = self._snapshot(
            team_id=self.teams[0].id, sprint_id=self.sprints[0].id
        )
        self.assertEqual(self._ids(filtered), set((self.visible - self.other).ids))
        self.assertEqual(filtered["total"], len(self.visible - self.other))
        for value in (True, -1, "1"):
            with self.assertRaises(ValidationError):
                self._snapshot(sprint_id=value)
        with self.assertRaises(AccessError):
            self._snapshot(team_id=self.teams[0].id, sprint_id=self.sprints[1].id)
        for grouping in ("stage", [], True):
            with self.assertRaises(ValidationError):
                self._snapshot(grouping=grouping)
        self.env["project.task"].create(
            [
                {
                    "name": f"Cursor swim {i}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.item_type.id,
                    "sprint_id": self.sprints[0].id,
                }
                for i in range(51)
            ]
        )
        cursor = self._snapshot()["next_cursor"]
        self.assertTrue(cursor)
        with self.assertRaises(ValidationError):
            self._snapshot(cursor=cursor, grouping="assignee")
        with self.assertRaises(ValidationError):
            self._snapshot(cursor=cursor, team_id=self.teams[0].id)

    def test_hidden_ancestors_and_sprints_never_grant_metadata_or_membership(self):
        self.env["ir.rule"].create(
            {
                "name": "Hidden Epic",
                "model_id": self.env["ir.model"]._get_id("project.task"),
                "domain_force": repr([("id", "!=", self.epic.id)]),
            }
        )
        self.env.invalidate_all()
        snapshot = self._snapshot()
        self.assertEqual(snapshot["total"], len(self.visible))
        self.assertNotIn("Visible Epic", json.dumps(snapshot))
        unknown = next(row for row in snapshot["lanes"] if row["id"] == "unknown")
        self.assertIn(self.nested.id, [row["id"] for row in unknown["items"]])
        self.env["ir.rule"].create(
            {
                "name": "Hidden Sprint",
                "model_id": self.env["ir.model"]._get_id("project.sprint"),
                "domain_force": repr([("id", "!=", self.sprints[0].id)]),
            }
        )
        self.env.invalidate_all()
        snapshot = self._snapshot()
        self.assertEqual(self._ids(snapshot), set(self.other.ids))
        self.assertEqual(snapshot["total"], len(self.other))
        with self.assertRaises(AccessError):
            self._snapshot(sprint_id=self.sprints[0].id)
        action = self.project.with_user(self.user).action_open_agile_swimlane_tasks()
        self.assertEqual(
            self.env["project.task"].with_user(self.user).search(action["domain"]),
            self.other.with_user(self.user),
        )

    def test_project_company_archive_and_native_stage_guards(self):
        company = self.env["res.company"].create({"name": "Foreign swim company"})
        foreign = self.env["project.project"].create(
            {
                "name": "Foreign swim",
                "agile_enabled": True,
                "agile_key": "FSWIM",
                "company_id": company.id,
                "privacy_visibility": "employees",
            }
        )
        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(
                self.user
            ).get_agile_swimlane_snapshot(foreign.id)
        private = self.env["project.project"].create(
            {
                "name": "Private swim",
                "agile_enabled": True,
                "agile_key": "PSWIM",
                "privacy_visibility": "followers",
            }
        )
        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(
                self.user
            ).get_agile_swimlane_snapshot(private.id)
        other_type = self.env["project.agile.item.type"].create(
            {"name": "Other swim type", "code": "other_swim"}
        )
        stage = self.env["project.task.type"].create(
            {
                "name": "Forbidden swim stage",
                "project_ids": [Command.link(self.project.id)],
                "agile_item_type_ids": [Command.link(other_type.id)],
            }
        )
        history = self._history()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.solo.with_user(self.user).write({"stage_id": stage.id})
        self.assertEqual(self.solo.stage_id, self.stages[0])
        self.assertEqual(history, self._history())
        self.project.active = False
        with self.assertRaises(AccessError):
            self._snapshot()

    def test_epic_at_exactly_32_ancestors_resolves_but_33_is_unknown(self):
        parent = self.epic
        for depth in range(31):
            parent = self._task(
                f"Deep context {depth}", parent_id=parent.id, sprint_id=False
            )
        at_bound = self._task("Epic 32 ancestors away", parent_id=parent.id)
        beyond = self._task("Epic 33 ancestors away", parent_id=at_bound.id)
        snapshot = self._snapshot()
        lanes = {
            lane["id"]: {row["id"] for row in lane["items"]}
            for lane in snapshot["lanes"]
        }
        self.assertEqual(lanes[f"epic:{self.epic.id}"], {self.nested.id, at_bound.id})
        self.assertEqual(lanes["unknown"], {beyond.id})
        self.assertEqual(
            self._ids(snapshot), set((self.visible | at_bound | beyond).ids)
        )

    def test_hidden_assignees_preserve_cardinality_without_disclosure(self):
        hidden_only = self._task(
            "Unavailable owner work", user_ids=[Command.set(self.other_user.ids)]
        )
        self.env["ir.rule"].create(
            {
                "name": "Hide other swim user",
                "model_id": self.env["ir.model"]._get_id("res.users"),
                "domain_force": repr([("id", "!=", self.other_user.id)]),
            }
        )
        self.env.invalidate_all()
        reader_tasks = (self.visible | hidden_only).with_user(self.user)
        self.assertFalse(
            self.env["res.users"]
            .with_user(self.user)
            .search([("id", "=", self.other_user.id)])
        )
        placement = reader_tasks.sudo().read(
            ["parent_id", "sprint_id", "stage_id", "user_ids"], load=None
        )
        history = self._history()
        reader_tasks.invalidate_recordset(["user_ids"])
        # Warm the relation through the same caller-bound read as the producer.
        reader_tasks.env["project.task"].search_fetch(
            [("id", "in", reader_tasks.ids)], ["name", "user_ids"]
        )
        # Warm the real caller-filtered relation; elevation must not reuse it.
        self.assertFalse(hidden_only.with_user(self.user).user_ids)
        self.assertEqual(self.shared.with_user(self.user).user_ids.ids, self.user.ids)
        snapshot = self._snapshot(grouping="assignee")
        reader_tasks.env["project.task"].search_fetch(
            [("id", "in", reader_tasks.ids)], ["name", "user_ids"]
        )
        self.assertFalse(hidden_only.with_user(self.user).user_ids)
        self.assertEqual(self.shared.with_user(self.user).user_ids.ids, self.user.ids)
        lanes = {
            lane["id"]: {row["id"] for row in lane["items"]}
            for lane in snapshot["lanes"]
        }
        self.assertEqual(lanes["multiple"], {self.shared.id})
        self.assertEqual(lanes["unknown"], {hidden_only.id})
        self.assertEqual(lanes[f"user:{self.user.id}"], {self.solo.id, self.nested.id})
        self.assertEqual(lanes["none"], {self.unassigned.id})
        self.assertEqual(snapshot["total"], len(reader_tasks))
        self.assertEqual(snapshot["shown"], len(reader_tasks))
        self.assertEqual(self._ids(snapshot), set(reader_tasks.ids))
        self.assertEqual(
            sum(len(lane["items"]) for lane in snapshot["lanes"]), len(reader_tasks)
        )
        self.assertNotIn(self.other_user.name, json.dumps(snapshot))
        self.assertNotIn(f"user:{self.other_user.id}", lanes)
        reader_tasks.invalidate_recordset(["user_ids"])
        self.assertEqual(
            placement,
            reader_tasks.sudo().read(
                ["parent_id", "sprint_id", "stage_id", "user_ids"], load=None
            ),
        )
        self.assertEqual(history, self._history())

    def test_draft_sprint_work_is_excluded_from_snapshot_and_list(self):
        draft = self.env["project.sprint"].create(
            {
                "name": "Draft swim",
                "project_id": self.project.id,
                "team_id": self.teams[0].id,
            }
        )
        task = self._task("Draft work", sprint_id=draft.id)
        self.assertIn(
            task,
            self.env["project.task"]
            .with_user(self.user)
            .search([("id", "=", task.id)]),
        )
        snapshot = self._snapshot()
        self.assertEqual(self._ids(snapshot), set(self.visible.ids))
        self.assertEqual(snapshot["total"], len(self.visible))
        action = self.project.with_user(self.user).action_open_agile_swimlane_tasks()
        self.assertEqual(
            set(
                self.env["project.task"]
                .with_user(self.user)
                .search(action["domain"])
                .ids
            ),
            set(self.visible.ids),
        )

    def test_hidden_stage_keeps_task_in_unavailable_column(self):
        self.env["ir.rule"].create(
            {
                "name": "Hide swim Doing stage",
                "model_id": self.env["ir.model"]._get_id("project.task.type"),
                "domain_force": repr([("id", "!=", self.stages[1].id)]),
            }
        )
        self.env.invalidate_all()
        self.assertFalse(
            self.env["project.task.type"]
            .with_user(self.user)
            .search([("id", "=", self.stages[1].id)])
        )
        snapshot = self._snapshot()
        self.assertEqual(self._ids(snapshot), set(self.visible.ids))
        self.assertEqual(snapshot["total"], len(self.visible))
        self.assertNotIn(self.stages[1].name, json.dumps(snapshot))
        self.assertEqual(
            {stage["id"] for stage in snapshot["stages"]}, {0, self.stages[0].id}
        )
        nested = next(
            item
            for lane in snapshot["lanes"]
            for item in lane["items"]
            if item["id"] == self.nested.id
        )
        self.assertEqual(nested["stage_id"], 0)

    def test_archived_independent_epic_ancestors_are_batched(self):
        second = self.env["project.task"].create(
            {
                "name": "Second archived Epic",
                "project_id": self.project.id,
                "agile_item_type_id": self.epic_type.id,
            }
        )
        (self.epic | second).write({"active": False})
        self.visible.write({"active": True})
        first_child = self._task("First archived Epic child", parent_id=self.epic.id)
        second_child = self._task("Second archived Epic child", parent_id=second.id)
        # Both parents are independently necessary in the same fetch frontier.
        snapshot = self._snapshot()
        lanes = {
            lane["id"]: {row["id"] for row in lane["items"]}
            for lane in snapshot["lanes"]
        }
        self.assertIn(first_child.id, lanes[f"epic:{self.epic.id}"])
        self.assertEqual(lanes[f"epic:{second.id}"], {second_child.id})
        self.assertEqual(
            self._ids(snapshot), set((self.visible | first_child | second_child).ids)
        )

    def test_native_list_accepts_100_sprints_and_rejects_101(self):
        teams = self.env["project.agile.team"].create(
            [
                {"name": f"Bound team {index}", "project_id": self.project.id}
                for index in range(99)
            ]
        )
        extra = self.env["project.sprint"].create(
            [
                {
                    "name": f"Bound Sprint {index}",
                    "project_id": self.project.id,
                    "team_id": team.id,
                }
                for index, team in enumerate(teams)
            ]
        )
        extra[:98].action_start()
        reader = self.project.with_user(self.user)
        action = reader.action_open_agile_swimlane_tasks()
        json.dumps(action)
        sprint_condition = next(
            condition[2]
            for condition in action["domain"]
            if isinstance(condition, (tuple, list)) and condition[0] == "sprint_id"
        )
        self.assertEqual(set(sprint_condition), set((self.sprints | extra[:98]).ids))
        extra[-1].action_start()
        with self.assertRaises(ValidationError):
            reader.action_open_agile_swimlane_tasks()
        selected = reader.action_open_agile_swimlane_tasks(sprint_id=self.sprints[0].id)
        self.assertEqual(
            set(
                self.env["project.task"]
                .with_user(self.user)
                .search(selected["domain"])
                .ids
            ),
            set((self.visible - self.other).ids),
        )

    def test_lane_window_requires_list_container(self):
        reader = self.project.with_user(self.user)
        for invalid in ((self.solo.id,), {"id": self.solo.id}, str(self.solo.id), True):
            with self.subTest(value=invalid), self.assertRaises(ValidationError):
                reader.action_open_agile_swimlane_tasks(task_ids=invalid)

    def test_lane_window_rejects_more_than_50_ids(self):
        reader = self.project.with_user(self.user)
        reader.action_open_agile_swimlane_tasks(task_ids=[self.solo.id] * 50)
        with self.assertRaises(ValidationError):
            reader.action_open_agile_swimlane_tasks(task_ids=[self.solo.id] * 51)

    def test_lane_window_requires_integer_ids_not_bool(self):
        for invalid in (True, False, str(self.solo.id), float(self.solo.id), None):
            with self.subTest(value=invalid), self.assertRaises(ValidationError):
                self.project.with_user(self.user).action_open_agile_swimlane_tasks(
                    task_ids=[invalid]
                )

    def test_lane_window_requires_positive_ids(self):
        for invalid in (0, -self.solo.id):
            with self.subTest(value=invalid), self.assertRaises(ValidationError):
                self.project.with_user(self.user).action_open_agile_swimlane_tasks(
                    task_ids=[invalid]
                )
        empty = self.project.with_user(self.user).action_open_agile_swimlane_tasks(
            task_ids=[]
        )
        self.assertFalse(
            self.env["project.task"].with_user(self.user).search(empty["domain"])
        )

    def test_cursor_binds_sprint_even_when_anchor_is_in_both_scopes(self):
        self.env["project.task"].create(
            [
                {
                    "name": f"Sprint cursor {index}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.item_type.id,
                    "sprint_id": self.sprints[0].id,
                }
                for index in range(51)
            ]
        )
        cursor = self._snapshot()["next_cursor"]
        self.assertTrue(cursor)
        self.assertIn(
            cursor["id"],
            self.env["project.task"]
            .with_user(self.user)
            .search([("sprint_id", "=", self.sprints[0].id)])
            .ids,
        )
        self.assertTrue(self._snapshot(sprint_id=self.sprints[0].id)["next_cursor"])
        with self.assertRaises(ValidationError):
            self._snapshot(cursor=cursor, sprint_id=self.sprints[0].id)

    def test_cursor_binds_revision_after_real_planning_change(self):
        self.env["project.task"].create(
            [
                {
                    "name": f"Revision cursor {index}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.item_type.id,
                    "sprint_id": self.sprints[0].id,
                }
                for index in range(51)
            ]
        )
        cursor = self._snapshot()["next_cursor"]
        self.assertTrue(cursor)
        anchor = self.env["project.task"].browse(cursor["id"])
        anchor_version = anchor.write_date
        revision = self.project.agile_planning_backlog_revision
        model = self.env["project.project"].with_user(self.user)
        model.apply_agile_planning_change(
            self.project.id,
            "return",
            self.other.ids,
            expected_versions={
                "tasks": {
                    str(self.other.id): model._agile_planning_record_version(self.other)
                },
                "sprints": {
                    str(self.sprints[1].id): model._agile_planning_record_version(
                        self.sprints[1]
                    )
                },
            },
        )
        self.assertFalse(self.other.sprint_id)
        self.assertEqual(anchor.write_date, anchor_version)
        self.assertEqual(self.project.agile_planning_backlog_revision, revision + 1)
        with self.assertRaises(ValidationError):
            self._snapshot(cursor=cursor)

    def test_assignee_projection_queries_do_not_grow_per_card(self):
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.cr.sql_log_count
        small = self._snapshot(grouping="assignee")
        small_queries = self.cr.sql_log_count - before
        self.assertEqual(small["shown"], 5)
        extra = self.env["project.task"].create(
            [
                {
                    "name": f"Batched owner {index}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.item_type.id,
                    "sprint_id": self.sprints[0].id,
                    "user_ids": [Command.clear()],
                }
                for index in range(45)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.cr.sql_log_count
        large = self._snapshot(grouping="assignee")
        large_queries = self.cr.sql_log_count - before
        self.assertEqual(large["shown"], 50)
        self.assertEqual(large["total"], 50)
        self.assertEqual(self._ids(large), set((self.visible | extra).ids))
        self.assertGreater(small_queries, 0)
        self.assertLessEqual(large_queries, small_queries)

    def test_real_two_axis_grouping_filters_and_keyboard_journey(self):
        before = self._placement()
        history = self._history()
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Swimlane Project",
                "res_model": "project.project",
                "res_id": self.project.id,
                "view_mode": "form",
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}", "agile_swimlanes", login=self.user.login
        )
        self.assertEqual(before, self._placement())
        self.assertEqual(history, self._history())

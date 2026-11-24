"""Caller-bound dates, complete paging and native rendered roadmap navigation."""

import json
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install", "agile_roadmap")
class TestAgileRoadmap(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            "roadmap_reader",
            groups="project_agile.group_agile_member,project.group_project_milestone",
        )
        cls.today = fields.Date.today()
        cls.project = cls.env["project.project"].create(
            {
                "name": "Roadmap Project",
                "agile_enabled": True,
                "agile_key": "ROAD",
                "allow_milestones": True,
                "privacy_visibility": "employees",
                "company_id": cls.env.company.id,
                "date_start": cls.today,
                "date": cls.today + timedelta(days=60),
            }
        )
        cls.teams = cls.env["project.agile.team"].create(
            [
                {"name": name, "project_id": cls.project.id}
                for name in ("Roadmap team", "Other roadmap team")
            ]
        )
        cls.item_type = cls.env["project.agile.item.type"].create(
            {
                "name": "Roadmap Story",
                "code": "roadmap_story",
                "can_schedule_in_sprint": True,
            }
        )
        cls.item_type.allowed_child_type_ids = [Command.link(cls.item_type.id)]
        cls.epic_type = cls.env.ref("project_agile.project_agile_item_type_epic")
        cls.epic_type.allowed_child_type_ids = [Command.link(cls.item_type.id)]
        cls.release = cls.env["project.milestone"].create(
            {
                "name": "Roadmap release",
                "project_id": cls.project.id,
                "deadline": cls.today + timedelta(days=30),
            }
        )
        cls.undated_release = cls.env["project.milestone"].create(
            {
                "name": "Unscheduled release",
                "project_id": cls.project.id,
            }
        )
        cls.epic = cls._task("Roadmap Epic", agile_item_type_id=cls.epic_type.id)
        cls.story = cls._task("Roadmap Story parent", parent_id=cls.epic.id)
        cls.nested = cls._task("Roadmap nested work", parent_id=cls.story.id)
        cls.undated = cls._task("Roadmap undated work", date_deadline=False)
        cls.other = cls._task("Other team deadline", agile_team_id=cls.teams[1].id)
        cls.outside = cls._task(
            "Later deadline", date_deadline=cls.today + timedelta(days=120)
        )
        cls.hidden = cls._task("Secret roadmap work")
        cls.closed = cls._task("Finished roadmap work", state="1_done")
        cls.archived = cls._task("Archived roadmap work", active=False)
        cls.env["ir.rule"].create(
            {
                "name": "Hide roadmap work",
                "model_id": cls.env["ir.model"]._get_id("project.task"),
                "domain_force": repr([("id", "!=", cls.hidden.id)]),
            }
        )

    @classmethod
    def _task(cls, name, **values):
        return cls.env["project.task"].create(
            {
                "name": name,
                "project_id": cls.project.id,
                "agile_item_type_id": cls.item_type.id,
                "agile_team_id": cls.teams[0].id,
                "milestone_id": cls.release.id,
                "date_deadline": cls.today + timedelta(days=20),
                **values,
            }
        )

    def _snapshot(self, **kwargs):
        args = {
            "project_id": self.project.id,
            "date_from": str(self.today),
            "date_to": str(self.today + timedelta(days=89)),
            **kwargs,
        }
        return (
            self.env["project.project"]
            .with_user(self.user)
            .get_agile_roadmap_snapshot(**args)
        )

    @staticmethod
    def _ids(snapshot):
        return {row["id"] for row in snapshot["work"]["items"]}

    def test_native_dates_nested_work_unscheduled_and_readonly_history(self):
        sprint = self.env["project.sprint"].create(
            {
                "name": "Independent Sprint",
                "project_id": self.project.id,
                "team_id": self.teams[0].id,
            }
        )
        self.nested.sprint_id = sprint
        sprint.action_start()
        history_fields = [
            "task_id",
            "event_type",
            "story_points",
            "event_at",
            "actor_id",
        ]
        before = sprint.scope_event_ids.read(history_fields, load=None)
        placement = (self.epic | self.story | self.nested).read(
            ["parent_id", "sprint_id", "date_deadline"], load=None
        )
        snapshot = self._snapshot()
        self.assertEqual(
            self._ids(snapshot),
            set((self.epic | self.story | self.nested | self.other).ids),
        )
        self.assertEqual(snapshot["project"]["start"], str(self.today))
        self.assertEqual(snapshot["project"]["end"], str(self.project.date))
        nested = next(
            row for row in snapshot["work"]["items"] if row["id"] == self.nested.id
        )
        self.assertEqual(nested["parent"]["id"], self.story.id)
        self.assertEqual(
            nested["end"], fields.Datetime.to_string(self.nested.date_deadline)
        )
        if not snapshot["native_task_start"]:
            self.assertTrue(all(not row["start"] for row in snapshot["work"]["items"]))
        self.assertEqual(
            snapshot["milestones"]["items"][0]["date"], str(self.release.deadline)
        )
        self.assertEqual(
            self._ids(self._snapshot(mode="unscheduled")), set(self.undated.ids)
        )
        self.assertEqual(
            [
                row["id"]
                for row in self._snapshot(mode="unscheduled")["milestones"]["items"]
            ],
            self.undated_release.ids,
        )
        self.assertEqual(before, sprint.scope_event_ids.read(history_fields, load=None))
        self.assertEqual(
            placement,
            (self.epic | self.story | self.nested).read(
                ["parent_id", "sprint_id", "date_deadline"], load=None
            ),
        )
        self.assertFalse(self.release.is_reached)
        self.release.is_reached = True
        self.assertTrue(self._snapshot()["milestones"]["items"][0]["reached"])

    def test_filters_native_forms_and_all_date_fallback(self):
        snapshot = self._snapshot(
            team_id=self.teams[0].id,
            item_type_id=self.item_type.id,
            milestone_id=self.release.id,
        )
        self.assertEqual(self._ids(snapshot), set((self.story | self.nested).ids))
        reader = self.project.with_user(self.user)
        action = reader.action_open_agile_roadmap_work(
            team_id=self.teams[0].id,
            item_type_id=self.item_type.id,
            milestone_id=self.release.id,
        )
        json.dumps(action)
        self.assertEqual(
            set(
                self.env["project.task"]
                .with_user(self.user)
                .search(action["domain"])
                .ids
            ),
            set((self.story | self.nested | self.undated | self.outside).ids),
        )
        self.assertEqual(
            reader.action_open_agile_planning_task(self.nested.id)["res_id"],
            self.nested.id,
        )
        self.assertEqual(
            reader.action_open_agile_roadmap_milestone(self.release.id)["res_id"],
            self.release.id,
        )
        with self.assertRaises(AccessError):
            reader.action_open_agile_planning_task(self.hidden.id)

    def test_complete_independent_pages_and_scope_boundaries(self):
        extra = self.env["project.task"].create(
            [
                {
                    "name": f"Roadmap page {index}",
                    "project_id": self.project.id,
                    "agile_item_type_id": self.item_type.id,
                    "date_deadline": self.today,
                }
                for index in range(53)
            ]
        )
        releases = self.env["project.milestone"].create(
            [
                {
                    "name": f"Roadmap release page {index}",
                    "project_id": self.project.id,
                    "deadline": self.today,
                }
                for index in range(51)
            ]
        )
        expected = set((self.epic | self.story | self.nested | self.other | extra).ids)
        first = self._snapshot()
        self.assertEqual(len(first["work"]["items"]), 50)
        self.assertEqual(first["work"]["total"], len(expected))
        self.assertEqual(len(first["milestones"]["items"]), 50)
        second = self._snapshot(
            task_cursor=first["work"]["next_cursor"],
            milestone_cursor=first["milestones"]["next_cursor"],
        )
        self.assertFalse(self._ids(first) & self._ids(second))
        self.assertEqual(self._ids(first) | self._ids(second), expected)
        self.assertFalse(second["work"]["next_cursor"])
        self.assertEqual(
            {
                row["id"]
                for page in (first, second)
                for row in page["milestones"]["items"]
            },
            set((self.release | releases).ids),
        )
        self.assertFalse(second["milestones"]["next_cursor"])
        with self.assertRaises(ValidationError):
            self._snapshot(task_cursor=first["work"]["next_cursor"], mode="unscheduled")
        with self.assertRaises(ValidationError):
            self._snapshot(
                task_cursor=first["work"]["next_cursor"],
                date_to=str(self.today + timedelta(days=90)),
            )
        self.assertTrue(
            self._snapshot(date_to=str(self.today + timedelta(days=365)))["work"]
        )
        for dates in (
            (str(self.today), str(self.today + timedelta(days=366))),
            ("bad", str(self.today)),
            (str(self.today), str(self.today - timedelta(days=1))),
        ):
            with self.subTest(dates=dates), self.assertRaises(ValidationError):
                self._snapshot(date_from=dates[0], date_to=dates[1])
        for value in (True, "1", -1):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self._snapshot(item_type_id=value)

    def test_hidden_related_labels_and_milestones_do_not_leak(self):
        for model, record in (
            ("project.task", self.story),
            ("project.agile.team", self.teams[0]),
            ("project.milestone", self.release),
        ):
            self.env["ir.rule"].create(
                {
                    "name": f"Hide roadmap context {model}",
                    "model_id": self.env["ir.model"]._get_id(model),
                    "domain_force": repr([("id", "!=", record.id)]),
                }
            )
        self.env.invalidate_all()
        snapshot = self._snapshot()
        nested = next(
            row for row in snapshot["work"]["items"] if row["id"] == self.nested.id
        )
        self.assertFalse(nested["parent"])
        self.assertTrue(nested["parent_unavailable"])
        self.assertFalse(nested["team"])
        self.assertFalse(nested["milestone"])
        self.assertEqual(snapshot["milestones"]["total"], 0)
        payload = json.dumps(snapshot)
        for name in (
            self.story.name,
            self.teams[0].name,
            self.release.name,
            self.hidden.name,
        ):
            self.assertNotIn(name, payload)
        for filters in (
            {"team_id": self.teams[0].id},
            {"milestone_id": self.release.id},
        ):
            with self.assertRaises(AccessError):
                self._snapshot(**filters)
        with self.assertRaises(AccessError):
            self.project.with_user(self.user).action_open_agile_roadmap_milestone(
                self.release.id
            )

    def test_project_company_and_optional_milestone_boundaries(self):
        company = self.env["res.company"].create({"name": "Foreign roadmap company"})
        for privacy, company_id, key in (
            ("followers", self.env.company.id, "PRIVROAD"),
            ("employees", company.id, "FORROAD"),
        ):
            project = self.env["project.project"].create(
                {
                    "name": "Unavailable roadmap",
                    "agile_enabled": True,
                    "agile_key": key,
                    "allow_milestones": True,
                    "privacy_visibility": privacy,
                    "company_id": company_id,
                }
            )
            release = self.env["project.milestone"].create(
                {"name": "Foreign release", "project_id": project.id}
            )
            with self.assertRaises(AccessError):
                self._snapshot(project_id=project.id)
            with self.assertRaises(AccessError):
                self._snapshot(milestone_id=release.id)
        self.project.allow_milestones = False
        snapshot = self._snapshot()
        self.assertFalse(snapshot["show_milestones"])
        self.assertFalse(snapshot["milestones"]["items"])
        self.assertTrue(
            all(not item["milestone"] for item in snapshot["work"]["items"])
        )
        with self.assertRaises(AccessError):
            self._snapshot(milestone_id=self.release.id)
        self.project.active = False
        with self.assertRaises(AccessError):
            self._snapshot()

    def test_real_project_button_dates_filters_and_native_navigation(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Roadmap Project",
                "res_model": "project.project",
                "res_id": self.project.id,
                "view_mode": "form",
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}", "agile_roadmap", login=self.user.login
        )
        self.assertFalse(self.release.is_reached)
        self.assertEqual(self.nested.parent_id, self.story)

    def test_real_native_milestone_drilldown(self):
        action = self.env["ir.actions.client"].create(
            {
                "name": "Roadmap release navigation",
                "tag": "project_agile_ui.roadmap",
                "context": repr({"project_id": self.project.id}),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}", "agile_roadmap_release", login=self.user.login
        )

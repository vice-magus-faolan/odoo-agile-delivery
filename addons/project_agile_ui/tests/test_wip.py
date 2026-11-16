"""Advisory counts must not become disclosure or transition authority."""

from psycopg2.errors import CheckViolation, UniqueViolation

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestAdvisoryWip(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reader = mail_new_test_user(
            cls.env, "wip_reader", groups="project.group_project_user"
        )
        cls.manager = mail_new_test_user(
            cls.env, "wip_manager", groups="project.group_project_manager"
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "WIP Project",
                "agile_enabled": True,
                "agile_key": "WIP",
                "privacy_visibility": "employees",
                "company_id": cls.env.company.id,
            }
        )
        cls.teams = cls.env["project.agile.team"].create(
            [
                {"name": name, "project_id": cls.project.id}
                for name in ("WIP A", "WIP B")
            ]
        )
        cls.sprints = cls.env["project.sprint"].create(
            [
                {"name": team.name, "project_id": cls.project.id, "team_id": team.id}
                for team in cls.teams
            ]
        )
        cls.stages = cls.env["project.task.type"].create(
            [
                {"name": name, "project_ids": [Command.link(cls.project.id)]}
                for name in ("WIP Doing", "WIP Review", "WIP Hidden only")
            ]
        )
        cls.kind = cls.env["project.agile.item.type"].create(
            {
                "name": "WIP work",
                "code": "wip_work",
                "can_schedule_in_sprint": True,
            }
        )
        cls.tasks = cls.env["project.task"].create(
            [
                {
                    "name": f"WIP work {index}",
                    "project_id": cls.project.id,
                    "agile_item_type_id": cls.kind.id,
                    "sprint_id": cls.sprints[0].id,
                    "stage_id": cls.stages[0].id,
                }
                for index in range(55)
            ]
        )
        cls.other = cls._task("Other team", sprint_id=cls.sprints[1].id)
        cls.hidden = cls._task("Hidden WIP") | cls._task(
            "Hidden-only stage", stage_id=cls.stages[2].id
        )
        cls.env["ir.rule"].create(
            {
                "name": "Hide WIP fixture work",
                "model_id": cls.env["ir.model"]._get_id("project.task"),
                "domain_force": repr([("id", "not in", cls.hidden.ids)]),
            }
        )
        cls.sprints.action_start()

    @classmethod
    def _task(cls, name, **values):
        return cls.env["project.task"].create(
            {
                "name": name,
                "project_id": cls.project.id,
                "agile_item_type_id": cls.kind.id,
                "sprint_id": cls.sprints[0].id,
                "stage_id": cls.stages[0].id,
                **values,
            }
        )

    def _enable(self):
        self.project.with_user(self.manager).write(
            {
                "agile_wip_enabled": True,
                "agile_wip_limit_ids": [
                    Command.create({"stage_id": stage.id, "limit": 2})
                    for stage in self.stages
                ],
            }
        )

    def _snapshot(self, **kwargs):
        return (
            self.env["project.project"]
            .with_user(self.reader)
            .get_agile_swimlane_snapshot(self.project.id, **kwargs)
        )

    def test_full_visible_scope_is_independent_of_pages_lanes_and_hidden_work(self):
        disabled = self._snapshot()
        self.assertFalse(disabled["wip_enabled"])
        self.assertEqual(disabled["wip"], [])
        self._enable()
        before = self.tasks.read(
            ["stage_id", "parent_id", "user_ids", "sprint_id"], load=None
        )
        history = self.sprints.scope_event_ids.read(load=None)
        first = self._snapshot()
        self.assertEqual(first["shown"], 50)
        self.assertEqual(first["total"], 56)
        expected = {
            self.stages[0].id: (56, 2, 54),
            self.stages[1].id: (0, 2, 0),
            self.stages[2].id: (0, 2, 0),
        }

        def totals(snapshot):
            return {
                row["id"]: (row["count"], row["limit"], row["overflow"])
                for row in snapshot["wip"]
            }

        self.assertEqual(totals(first), expected)
        second = self._snapshot(cursor=first["next_cursor"])
        self.assertEqual(second["shown"], 6)
        self.assertEqual(totals(second), expected)
        self.assertEqual(totals(self._snapshot(grouping="assignee")), expected)
        filtered = self._snapshot(
            team_id=self.teams[1].id, sprint_id=self.sprints[1].id
        )
        self.assertEqual(filtered["wip"][0]["count"], 1)
        self.assertEqual(filtered["wip"][0]["overflow"], 0)
        self.assertEqual(
            before,
            self.tasks.read(
                ["stage_id", "parent_id", "user_ids", "sprint_id"], load=None
            ),
        )
        self.assertEqual(history, self.sprints.scope_event_ids.read(load=None))
        self.env["ir.rule"].create(
            {
                "name": "Hide WIP stage",
                "model_id": self.env["ir.model"]._get_id("project.task.type"),
                "domain_force": repr([("id", "!=", self.stages[2].id)]),
            }
        )
        self.env.invalidate_all()
        self.assertNotIn(
            self.stages[2].id, {row["id"] for row in self._snapshot()["wip"]}
        )
        # Ordinary configuration reads must not reveal the hidden stage either.
        self.assertFalse(
            self.env["project.agile.wip.limit"]
            .with_user(self.reader)
            .search(
                [
                    ("project_id", "=", self.project.id),
                    ("stage_id", "=", self.stages[2].id),
                ]
            )
        )

    def test_advisory_settings_and_native_bulk_transitions(self):
        self._enable()
        original_events = self.sprints.scope_event_ids
        history = original_events.read(load=None)
        tasks = self.tasks.with_user(self.reader)
        tasks.write({"stage_id": self.stages[1].id})
        self.assertEqual(self._snapshot()["wip"][1]["overflow"], 53)
        tasks[:2].write({"state": "1_done"})
        tasks[2:4].write({"state": "1_canceled"})
        tasks[4:6].write({"active": False})
        self.assertEqual(self._snapshot()["wip"][1]["count"], 49)
        tasks[6:8].write({"stage_id": self.stages[0].id})
        self.assertEqual(self._snapshot()["wip"][1]["count"], 47)
        policy = self.project.agile_wip_limit_ids.filtered(
            lambda row: row.stage_id == self.stages[1]
        )
        policy.with_user(self.manager).write({"limit": 47})
        self.assertEqual(self._snapshot()["wip"][1]["overflow"], 0)
        policy.with_user(self.manager).write({"limit": 1})
        self.assertEqual(self._snapshot()["wip"][1]["overflow"], 46)
        self.project.with_user(self.manager).write({"agile_wip_enabled": False})
        self.assertEqual(self._snapshot()["wip"], [])
        self.project.with_user(self.manager).write({"agile_wip_enabled": True})
        self.assertEqual(self._snapshot()["wip"][1]["count"], 47)
        self.assertEqual(history, original_events.read(load=None))
        completed = self.sprints.scope_event_ids - original_events
        self.assertEqual(len(completed), 2)
        self.assertEqual(set(completed.mapped("event_type")), {"completed"})
        self.assertEqual(set(completed.task_id.ids), set(self.tasks[:2].ids))

    def test_configuration_authority_defaults_and_scope(self):
        self._enable()
        policy = self.project.agile_wip_limit_ids[0]
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.project.with_user(self.reader).write({"agile_wip_enabled": False})
        with self.assertRaises(AccessError), self.cr.savepoint():
            policy.with_user(self.reader).write({"limit": 99})
        with self.assertRaises(AccessError), self.cr.savepoint():
            policy.with_user(self.reader).unlink()
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.env["project.agile.wip.limit"].with_user(self.reader).with_context(
                default_project_id=self.project.id, default_limit=99
            ).create({"stage_id": self.stages[0].id})
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.project.with_user(self.reader).write(
                {
                    "agile_wip_limit_ids": [Command.update(policy.id, {"limit": 99})],
                }
            )
        with self.assertRaises(CheckViolation), self.cr.savepoint():
            policy.with_user(self.manager).write({"limit": 0})
        with self.assertRaises(UniqueViolation), self.cr.savepoint():
            self.env["project.agile.wip.limit"].with_user(self.manager).create(
                {
                    "project_id": self.project.id,
                    "stage_id": policy.stage_id.id,
                    "limit": 3,
                }
            )
        private = self.env["project.project"].create(
            {
                "name": "Private WIP",
                "agile_enabled": True,
                "agile_key": "PRIVATEWIP",
                "privacy_visibility": "followers",
            }
        )
        private_stage = self.env["project.task.type"].create(
            {
                "name": "Private stage",
                "project_ids": [Command.link(private.id)],
            }
        )
        private_policy = self.env["project.agile.wip.limit"].create(
            {
                "project_id": private.id,
                "stage_id": private_stage.id,
                "limit": 1,
            }
        )
        self.assertFalse(
            self.env["project.agile.wip.limit"]
            .with_user(self.reader)
            .search([("id", "=", private_policy.id)])
        )
        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(
                self.reader
            ).get_agile_swimlane_snapshot(private.id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.with_user(self.manager).write({"project_id": private.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.with_user(self.manager).write({"stage_id": private_stage.id})
        company = self.env["res.company"].create({"name": "Foreign WIP"})
        private.write({"company_id": company.id, "privacy_visibility": "employees"})
        self.assertFalse(
            self.env["project.agile.wip.limit"]
            .with_user(self.manager)
            .search([("id", "=", private_policy.id)])
        )
        with self.assertRaises(AccessError):
            self.env["project.project"].with_user(
                self.reader
            ).get_agile_swimlane_snapshot(private.id)

    def test_project_sprint_and_team_scope_not_stage_folding(self):
        self._enable()
        draft = self.env["project.sprint"].create(
            {
                "name": "Draft WIP",
                "project_id": self.project.id,
                "team_id": self.teams[0].id,
            }
        )
        self._task("Draft work", sprint_id=draft.id)
        other_project = self.env["project.project"].create(
            {
                "name": "Other WIP Project",
                "agile_enabled": True,
                "agile_key": "OTHERWIP",
                "privacy_visibility": "employees",
            }
        )
        self.stages[0].write(
            {"project_ids": [Command.link(other_project.id)], "fold": True}
        )
        other_team = self.env["project.agile.team"].create(
            {
                "name": "Other Project team",
                "project_id": other_project.id,
            }
        )
        other_sprint = self.env["project.sprint"].create(
            {
                "name": "Other Project Sprint",
                "project_id": other_project.id,
                "team_id": other_team.id,
            }
        )
        self._task(
            "Other Project work", project_id=other_project.id, sprint_id=other_sprint.id
        )
        other_sprint.action_start()
        self.assertEqual(self._snapshot()["wip"][0]["count"], 56)
        self.env["ir.rule"].create(
            {
                "name": "Hide first WIP Sprint",
                "model_id": self.env["ir.model"]._get_id("project.sprint"),
                "domain_force": repr([("id", "!=", self.sprints[0].id)]),
            }
        )
        self.env.invalidate_all()
        self.assertEqual(self._snapshot()["wip"][0]["count"], 1)
        with self.assertRaises(AccessError):
            self._snapshot(sprint_id=self.sprints[0].id)
        self.teams[1].write({"active": False})
        self.assertEqual(self._snapshot()["wip"][0]["count"], 0)

    def _make_project_read_only_for_manager(self, project):
        self.env["ir.rule"].create(
            {
                "name": "Deny WIP fixture Project writes",
                "model_id": self.env["ir.model"]._get_id("project.project"),
                "domain_force": repr([("id", "!=", project.id)]),
                "perm_read": False,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        self.env.invalidate_all()
        subject = project.with_user(self.manager)
        self.assertFalse(subject.env.su)
        self.assertTrue(subject.env.user.has_group("project.group_project_manager"))
        subject.check_access("read")
        self.assertFalse(subject.has_access("write"))
        return subject

    def test_create_requires_project_write_access(self):
        project = self._make_project_read_only_for_manager(self.project)
        stage = self.stages[0].with_user(self.manager)
        stage.check_access("read")
        self.assertTrue(project.agile_enabled)
        self.assertIn(project, stage.project_ids)
        policies = self.env["project.agile.wip.limit"].with_user(self.manager)
        domain = [("project_id", "=", project.id), ("stage_id", "=", stage.id)]
        self.assertFalse(policies.search(domain))
        with self.assertRaises(AccessError), self.cr.savepoint():
            policies.create(
                {"project_id": project.id, "stage_id": stage.id, "limit": 2}
            )
        self.assertFalse(policies.search(domain))

    def test_unlink_requires_project_configuration_access(self):
        self._enable()
        policy = self.project.agile_wip_limit_ids[0].with_user(self.manager)
        project = self._make_project_read_only_for_manager(self.project)
        policy.check_access("read")
        policy.check_access("unlink")
        policy.stage_id.check_access("read")
        self.assertEqual(policy.project_id, project)
        with self.assertRaises(AccessError), self.cr.savepoint():
            policy.unlink()
        self.assertEqual(policy.exists(), policy)
        self.assertEqual(policy.project_id, project)

    def test_policy_cannot_move_to_readable_project_with_shared_stage(self):
        self._enable()
        destination = self.env["project.project"].create(
            {
                "name": "Read-only WIP destination",
                "agile_enabled": True,
                "agile_key": "WIPDEST",
                "privacy_visibility": "employees",
                "company_id": self.project.company_id.id,
            }
        )
        policy = self.project.agile_wip_limit_ids[0].with_user(self.manager)
        policy.stage_id.write({"project_ids": [Command.link(destination.id)]})
        destination = self._make_project_read_only_for_manager(destination)
        source = self.project.with_user(self.manager)
        source.check_access("write")
        policy.check_access("write")
        policy.stage_id.check_access("read")
        self.assertTrue(destination.agile_enabled)
        self.assertIn(source, policy.stage_id.project_ids)
        self.assertIn(destination, policy.stage_id.project_ids)
        self.assertFalse(
            self.env["project.agile.wip.limit"]
            .with_user(self.manager)
            .search([("project_id", "=", destination.id)])
        )
        with (
            self.assertRaisesRegex(
                ValidationError, "A WIP limit cannot move to another Project"
            ),
            self.cr.savepoint(),
        ):
            policy.write({"project_id": destination.id})
        self.assertEqual(policy.project_id, source)

    def test_non_agile_project_rejected_with_belonging_stage(self):
        project = self.env["project.project"].create(
            {"name": "Plain WIP Project", "privacy_visibility": "employees"}
        )
        stage = self.env["project.task.type"].create(
            {"name": "Plain WIP stage", "project_ids": [Command.link(project.id)]}
        )
        project = project.with_user(self.manager)
        stage = stage.with_user(self.manager)
        self.assertFalse(project.env.su)
        self.assertTrue(project.env.user.has_group("project.group_project_manager"))
        project.check_access("write")
        stage.check_access("read")
        self.assertFalse(project.agile_enabled)
        self.assertIn(project, stage.project_ids)
        policies = self.env["project.agile.wip.limit"].with_user(self.manager)
        domain = [("project_id", "=", project.id), ("stage_id", "=", stage.id)]
        self.assertFalse(policies.search(domain))
        with (
            self.assertRaisesRegex(
                ValidationError, "Choose a stage belonging to this Agile Project"
            ),
            self.cr.savepoint(),
        ):
            policies.create(
                {"project_id": project.id, "stage_id": stage.id, "limit": 2}
            )
        self.assertFalse(policies.search(domain))

    def test_summary_excludes_detached_but_readable_stage(self):
        self._enable()
        other_project = self.env["project.project"].create(
            {"name": "Shared WIP stage Project", "privacy_visibility": "employees"}
        )
        stage = self.stages[1]
        stage.write({"project_ids": [Command.link(other_project.id)]})
        policy = self.project.agile_wip_limit_ids.filtered(
            lambda row: row.stage_id == stage
        ).with_user(self.reader)
        self.assertFalse(policy.env.su)
        policy.check_access("read")
        self.assertIn(stage.id, {row["id"] for row in self._snapshot()["wip"]})
        stage.write({"project_ids": [Command.unlink(self.project.id)]})
        stage = stage.with_user(self.reader)
        stage.check_access("read")
        other_project.with_user(self.reader).check_access("read")
        self.assertIn(other_project, stage.project_ids)
        self.assertNotIn(self.project, stage.project_ids)
        self.assertEqual(policy.exists(), policy)
        policy.check_access("read")
        self.assertEqual(policy.stage_id, stage)
        self.assertNotIn(stage.id, {row["id"] for row in self._snapshot()["wip"]})

    def test_project_administrator_still_requires_native_project_write_access(self):
        self._enable()
        policy = self.project.agile_wip_limit_ids[0]
        self.env["ir.rule"].create(
            {
                "name": "Read-only WIP Project",
                "model_id": self.env["ir.model"]._get_id("project.project"),
                "domain_force": repr([("id", "!=", self.project.id)]),
                "perm_read": False,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        self.env.invalidate_all()
        self.project.with_user(self.manager).check_access("read")
        with self.assertRaises(AccessError), self.cr.savepoint():
            policy.with_user(self.manager).write({"limit": 99})
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.project.with_user(self.manager).write({"agile_wip_enabled": False})

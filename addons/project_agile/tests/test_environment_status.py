from unittest.mock import patch

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.mail.tests.common import mail_new_test_user


class TestEnvironmentStatus(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.member = mail_new_test_user(
            cls.env, "environment_member", groups="project_agile.group_agile_member"
        )
        cls.manager = mail_new_test_user(
            cls.env, "environment_manager", groups="project.group_project_manager"
        )
        cls.configuration = cls.env.ref(
            "project_agile.project_agile_item_type_configuration"
        )
        cls.data_import = cls.env.ref(
            "project_agile.project_agile_item_type_data_import"
        )
        cls.story = cls.env.ref("project_agile.project_agile_item_type_story")
        cls.projects = cls.env["project.project"].create(
            [
                {
                    "name": "E2E client",
                    "agile_enabled": True,
                    "agile_key": "ENVONE",
                    "privacy_visibility": "employees",
                },
                {
                    "name": "Staging client",
                    "agile_enabled": True,
                    "agile_key": "ENVTWO",
                    "privacy_visibility": "employees",
                },
            ]
        )
        cls.environments = cls.env["project.agile.environment"]
        for project, names in zip(
            cls.projects,
            (("E2E", "UAT", "Pre-Production", "Production"), ("Staging", "Production")),
            strict=False,
        ):
            cls.environments |= (
                cls.env["project.agile.environment"]
                .with_user(cls.manager)
                .create(
                    [
                        {
                            "name": name,
                            "sequence": index * 10,
                            "project_id": project.id,
                            "is_production": name == "Production",
                        }
                        for index, name in enumerate(names)
                    ]
                )
            )
        cls.tasks = (
            cls.env["project.task"]
            .with_user(cls.member)
            .create(
                [
                    {
                        "name": "Configure taxes",
                        "project_id": project.id,
                        "agile_item_type_id": cls.configuration.id,
                    }
                    for project in cls.projects
                ]
            )
        )

    def test_independent_ordered_environments_and_opt_in(self):
        self.assertTrue(self.configuration.tracks_environments)
        self.assertTrue(self.data_import.tracks_environments)
        self.assertEqual(
            self.projects[0].agile_environment_ids.mapped("name"),
            ["E2E", "UAT", "Pre-Production", "Production"],
        )
        self.assertEqual(
            self.projects[1].agile_environment_ids.mapped("name"),
            ["Staging", "Production"],
        )
        for task, expected in zip(self.tasks, (4, 2), strict=False):
            self.assertEqual(len(task.agile_environment_status_ids), expected)
            self.assertEqual(
                task.agile_environment_status_ids.mapped("status"), ["todo"] * expected
            )
            self.assertEqual(task.agile_environment_status_ids.actor_id, self.member)
            self.assertTrue(all(task.agile_environment_status_ids.mapped("changed_at")))
        ordinary = self.tasks[0].copy({"agile_item_type_id": self.story.id})
        self.assertFalse(ordinary.agile_environment_status_ids)
        imported = self.tasks[0].copy({"agile_item_type_id": self.data_import.id})
        self.assertEqual(len(imported.agile_environment_status_ids), 4)
        plain = self.env["project.project"].create({"name": "Plain"})
        native = self.env["project.task"].create(
            {
                "name": "Plain import",
                "project_id": plain.id,
                "agile_item_type_id": self.data_import.id,
            }
        )
        self.assertFalse(native.agile_environment_status_ids)

    def test_status_actor_gap_pairs_and_production_first(self):
        task = self.tasks[0]
        uat = task.project_id.agile_environment_ids.filtered(lambda e: e.name == "UAT")
        production = task.project_id.agile_environment_ids.filtered("is_production")
        lines = task.agile_environment_status_ids
        prod_line = lines.filtered(lambda line: line.environment_id == production)
        prod_line.with_user(self.member).with_context(tracking_disable=True).write(
            {"status": "done"}
        )
        self.assertEqual(prod_line.actor_id, self.member)
        self.assertTrue(prod_line.changed_at)
        self.assertEqual(
            lines.filtered(lambda line: line.environment_id == uat).status, "todo"
        )
        tasks = self.env["project.task"].with_user(self.member)
        gap = [
            ("agile_done_environment_id", "in", uat.ids),
            ("agile_pending_environment_id", "in", production.ids),
        ]
        # A different environment's done status must not satisfy UAT's predicate.
        self.assertNotIn(task, tasks.search(gap))
        lines.filtered(lambda line: line.environment_id == uat).write(
            {"status": "verified"}
        )
        self.assertNotIn(task, tasks.search(gap))
        prod_line.write({"status": "todo"})
        self.assertEqual(tasks.search(gap), task)
        foreign_prod = self.projects[1].agile_environment_ids.filtered("is_production")
        self.assertNotIn(
            task,
            tasks.search([("agile_pending_environment_id", "in", foreign_prod.ids)]),
        )

    def test_add_archive_reactivate_and_type_history(self):
        task = self.tasks[0]
        closed = task.copy({"name": "Finished", "state": "1_done"}) | task.copy(
            {"name": "Canceled", "state": "1_canceled"}
        )
        archived = task.copy({"name": "Archived open work", "active": False})
        history = (closed | archived).agile_environment_status_ids
        snapshot = history.read(["status", "actor_id", "changed_at"])
        project = task.project_id.with_user(self.manager)
        # The native settings relation passes active_test=False to its comodel.
        project.write({"agile_environment_ids": [Command.create({"name": "Pilot"})]})
        extra = project.agile_environment_ids.filtered(lambda e: e.name == "Pilot")
        line = task.agile_environment_status_ids.filtered(
            lambda line: line.environment_id == extra
        )
        self.assertEqual(line.status, "todo")
        self.assertNotIn(extra, closed.agile_environment_status_ids.environment_id)
        self.assertNotIn(extra, archived.agile_environment_status_ids.environment_id)
        self.assertNotIn(
            extra, self.tasks[1].agile_environment_status_ids.environment_id
        )
        line.with_user(self.member).write({"status": "done"})
        actor, changed_at, identity = line.actor_id, line.changed_at, line.id
        project.write(
            {"agile_environment_ids": [Command.update(extra.id, {"active": False})]}
        )
        self.assertFalse(line.applicable)
        self.assertEqual(
            (line.status, line.actor_id, line.changed_at), ("done", actor, changed_at)
        )
        with self.assertRaises(ValidationError):
            line.write({"status": "verified"})
        incoming = task.copy({"name": "Open work while Pilot is archived"})
        self.assertNotIn(extra, incoming.agile_environment_status_ids.environment_id)
        project.write(
            {"agile_environment_ids": [Command.update(extra.id, {"active": True})]}
        )
        self.assertTrue(line.applicable)
        self.assertEqual(line.id, identity)
        self.assertEqual(
            (line.status, line.actor_id, line.changed_at), ("done", actor, changed_at)
        )
        self.assertIn(extra, incoming.agile_environment_status_ids.environment_id)
        self.assertNotIn(extra, closed.agile_environment_status_ids.environment_id)
        self.assertNotIn(extra, archived.agile_environment_status_ids.environment_id)
        archived.with_user(self.member).write({"active": True})
        self.assertIn(extra, archived.agile_environment_status_ids.environment_id)
        self.assertEqual(history.read(["status", "actor_id", "changed_at"]), snapshot)
        task.write({"agile_item_type_id": self.story.id})
        self.assertFalse(line.applicable)
        task.write({"agile_item_type_id": self.configuration.id})
        self.assertTrue(line.applicable)
        self.assertEqual(line.status, "done")
        with self.assertRaises(ValidationError):
            extra.unlink()
        with self.assertRaises(AccessError):
            line.with_user(self.member).unlink()

    def test_name_and_id_search_operators_across_clients(self):
        tasks = self.env["project.task"].with_user(self.member)
        uat = self.env["project.agile.environment"].create(
            {"name": "UAT", "project_id": self.projects[1].id}
        )
        self.tasks.agile_environment_status_ids.filtered(
            lambda line: line.environment_id.name == "UAT"
        ).write({"status": "verified"})
        preproduction = self.tasks[0].agile_environment_status_ids.filtered(
            lambda line: line.environment_id.name == "Pre-Production"
        )
        preproduction.write({"status": "done"})
        preproduction_only = self.tasks[0].copy({"name": "Only pre-production done"})
        preproduction_only.agile_environment_status_ids.filtered(
            lambda line: line.environment_id == preproduction.environment_id
        ).write({"status": "done"})
        view = tasks.get_view(
            self.env.ref("project_agile.view_task_search_agile").id, "search"
        )
        search = etree.fromstring(view["arch"].encode())
        typed = {}
        for field, name in (
            ("agile_done_environment_id", "uAt"),
            ("agile_pending_environment_id", "production"),
            ("agile_done_environment_id", "production"),
            ("agile_done_environment_id", "pre-production"),
        ):
            node = search.xpath(f"//field[@name='{field}']")[0]
            typed[field, name] = safe_eval(
                node.get("filter_domain")
                or repr([(field, node.get("operator", "ilike"), name)]),
                {"self": name, "raw_value": name},
            )
        gap = (
            typed["agile_done_environment_id", "uAt"]
            + typed["agile_pending_environment_id", "production"]
        )
        self.assertEqual(tasks.search(gap), self.tasks)
        self.assertFalse(tasks.search(typed["agile_done_environment_id", "production"]))
        self.assertEqual(
            tasks.search(typed["agile_done_environment_id", "pre-production"]),
            self.tasks[0] | preproduction_only,
        )
        # Explicit advanced ORM patterns keep their native substring semantics.
        pattern_gap = [
            ("agile_done_environment_id", "ilike", "ua"),
            ("agile_pending_environment_id", "ilike", "pROd"),
        ]
        self.assertEqual(tasks.search(pattern_gap), self.tasks[1])
        for operator, pattern in (
            ("ilike", "ua"),
            ("like", "UA"),
            ("=ilike", "uat"),
            ("=like", "UAT"),
        ):
            self.assertEqual(
                tasks.search([("agile_done_environment_id", operator, pattern)]),
                self.tasks,
            )
            self.assertEqual(
                tasks.search([("agile_pending_environment_id", operator, pattern)]),
                preproduction_only,
            )
        for operator in ("not ilike", "not like"):
            self.assertEqual(
                tasks.search([("agile_done_environment_id", operator, "UAT")]),
                preproduction_only,
            )
            self.assertEqual(
                tasks.search([("agile_pending_environment_id", operator, "UAT")]),
                self.tasks,
            )
        for field in ("agile_done_environment_id", "agile_pending_environment_id"):
            for operator in ("ilike", "not ilike", "like", "not like"):
                self.assertFalse(
                    tasks.search([(field, operator, "No such environment")])
                )
        for operator, value in (("=", uat.id), ("in", uat.ids)):
            self.assertEqual(
                tasks.search([("agile_done_environment_id", operator, value)]),
                self.tasks[1],
            )
        for operator, value in (("!=", uat.id), ("not in", uat.ids)):
            self.assertFalse(
                tasks.search([("agile_done_environment_id", operator, value)])
            )
            self.assertEqual(
                tasks.search([("agile_pending_environment_id", operator, value)]),
                self.tasks[1],
            )
        self.tasks[1].agile_environment_status_ids.filtered(
            lambda line: line.environment_id.is_production
        ).write({"status": "done"})
        self.assertEqual(tasks.search(gap), self.tasks[0])
        self.projects[0].agile_environment_ids.filtered(
            lambda environment: environment.name == "UAT"
        ).write({"active": False})
        self.assertFalse(tasks.search(gap))

    def test_waiting_for_production_flags_and_missing_lines(self):
        tasks = self.env["project.task"].with_user(self.member)
        waiting = [("agile_waiting_for_production", "=", True)]
        self.assertFalse(tasks.search(waiting))
        self.tasks.agile_environment_status_ids.filtered(
            lambda line: not line.environment_id.is_production
        ).write({"status": "verified"})
        self.assertEqual(tasks.search(waiting), self.tasks)
        production = self.projects[0].agile_environment_ids.filtered("is_production")
        production.write({"name": "Live client", "active": False})
        self.assertEqual(tasks.search(waiting), self.tasks[1])
        production.write({"active": True})
        self.assertEqual(tasks.search(waiting), self.tasks)
        self.tasks[1].agile_environment_status_ids.filtered(
            lambda line: line.environment_id.is_production
        ).write({"status": "done"})
        self.assertEqual(tasks.search(waiting), self.tasks[0])
        ordinary = self.tasks[0].copy({"agile_item_type_id": self.story.id})
        self.assertNotIn(ordinary, tasks.search(waiting))
        # Done and canceled work do not receive newly added environment lines.
        closed = self.tasks[0].copy({"state": "1_done"}) | self.tasks[0].copy(
            {"state": "1_canceled"}
        )
        closed.agile_environment_status_ids.filtered(
            lambda line: line.environment_id.name == "E2E"
        ).write({"status": "done"})
        production.write({"is_production": False})
        # Model legacy missing rows before backfill, without deleting status history.
        with patch.object(
            type(self.projects), "_sync_open_environment_tasks", lambda projects: None
        ):
            extra = self.env["project.agile.environment"].create(
                {
                    "name": "Release",
                    "project_id": self.projects[0].id,
                    "is_production": True,
                }
            )
        self.assertNotIn(extra, closed.agile_environment_status_ids.environment_id)
        pending = [("agile_pending_environment_id", "=ilike", "release")]
        self.assertEqual(tasks.search(waiting), self.tasks[0])
        self.assertEqual(tasks.search(pending), self.tasks[0])
        self.assertNotIn(
            extra, self.tasks[0].agile_environment_status_ids.environment_id
        )
        self.projects[0]._sync_open_environment_tasks()
        self.assertNotIn(extra, closed.agile_environment_status_ids.environment_id)
        self.assertEqual(tasks.search(waiting), self.tasks[0])
        self.assertEqual(tasks.search(pending), self.tasks[0])
        history = closed.agile_environment_status_ids
        snapshot = history.read(["status", "actor_id", "changed_at"])
        closed.write({"state": "01_in_progress"})
        release_lines = closed.agile_environment_status_ids.filtered(
            lambda line: line.environment_id == extra
        )
        self.assertEqual(len(release_lines), 2)
        self.assertEqual(release_lines.mapped("status"), ["todo", "todo"])
        self.assertEqual(history.read(["status", "actor_id", "changed_at"]), snapshot)
        self.assertEqual(tasks.search(waiting), self.tasks[0] | closed)
        self.assertEqual(tasks.search(pending), self.tasks[0] | closed)
        closed[0].write({"state": "1_done"})
        closed[1].write({"state": "1_canceled"})
        self.assertEqual(tasks.search(pending), self.tasks[0] | closed)
        release_lines.with_user(self.member).write({"status": "verified"})
        self.assertEqual(tasks.search(waiting), self.tasks[0])
        self.assertEqual(tasks.search(pending), self.tasks[0])
        self.tasks[0].agile_environment_status_ids.filtered(
            lambda line: line.environment_id == extra
        ).write({"status": "verified"})
        self.assertNotIn(self.tasks[0], tasks.search(waiting))
        extra.write({"is_production": False})
        self.assertFalse(closed & tasks.search(waiting))
        self.assertNotIn(self.tasks[0], tasks.search(waiting))

    def test_name_search_honors_environment_rules_without_picker_limit(self):
        environments = self.env["project.agile.environment"].create(
            [
                {"name": "Pilot", "project_id": self.projects[0].id}
                for _index in range(12)
            ]
        )
        task = self.tasks[0]
        task.agile_environment_status_ids.filtered(
            lambda line: line.environment_id == environments[-1]
        ).write({"status": "done"})
        tasks = self.env["project.task"].with_user(self.member)
        done = [("agile_done_environment_id", "ilike", "pilot")]
        self.assertEqual(tasks.search(done), task)
        self.env["ir.rule"].create(
            {
                "name": "Hide Pilot environments from search",
                "model_id": self.env["ir.model"]._get_id("project.agile.environment"),
                "domain_force": repr([("id", "not in", environments.ids)]),
            }
        )
        self.assertFalse(tasks.search(done))
        self.assertFalse(
            tasks.search([("agile_pending_environment_id", "ilike", "pilot")])
        )

    def test_task_and_project_template_restore_and_copies(self):
        task = self.tasks[0]
        original_ids = task.agile_environment_status_ids.ids
        task.agile_environment_status_ids[0].write({"status": "done"})
        copied = task.copy()
        self.assertFalse(
            set(original_ids) & set(copied.agile_environment_status_ids.ids)
        )
        self.assertEqual(
            set(copied.agile_environment_status_ids.mapped("status")), {"todo"}
        )
        task.with_user(self.manager).action_convert_to_template()
        self.assertFalse(any(task.agile_environment_status_ids.mapped("applicable")))
        task.with_user(self.manager).action_undo_convert_to_template()
        self.assertEqual(task.agile_environment_status_ids.ids, original_ids)
        self.assertTrue(all(task.agile_environment_status_ids.mapped("applicable")))
        template = self.env["project.task"].create(
            {
                "name": "Template import",
                "project_id": self.projects[0].id,
                "is_template": True,
                "agile_item_type_id": self.data_import.id,
            }
        )
        self.assertFalse(template.agile_environment_status_ids)
        template.with_user(self.manager).action_undo_convert_to_template()
        self.assertEqual(len(template.agile_environment_status_ids), 4)
        project_copy = self.projects[0].copy(
            {"agile_enabled": True, "agile_key": "ENVCOPY"}
        )
        self.assertFalse(project_copy.agile_environment_ids)
        self.assertFalse(project_copy.task_ids.agile_environment_status_ids)
        self.assertEqual(task.agile_environment_status_ids.ids, original_ids)
        project_template = self.env["project.project"].create(
            {
                "name": "Template",
                "agile_enabled": True,
                "agile_key": "ENVTEMPLATE",
                "is_template": True,
            }
        )
        self.env["project.agile.environment"].create(
            {"name": "UAT", "project_id": project_template.id}
        )
        work = self.env["project.task"].create(
            {
                "name": "Template work",
                "project_id": project_template.id,
                "agile_item_type_id": self.configuration.id,
            }
        )
        self.assertFalse(work.agile_environment_status_ids)
        project_template.with_user(self.manager).action_undo_convert_to_template()
        self.assertEqual(len(work.agile_environment_status_ids), 1)

    def test_config_and_status_authority_and_forged_inputs(self):
        task = self.tasks[0]
        line = task.agile_environment_status_ids[0]
        with self.assertRaises(AccessError):
            task.project_id.with_user(self.member).write(
                {"name": "Not a Project administrator"}
            )
        line.with_user(self.member).write({"status": "verified"})
        line.with_user(self.manager).write({"message_follower_ids": [Command.clear()]})
        self.assertEqual(line.actor_id, self.member)
        quick = (
            self.env["project.task"]
            .with_user(self.member)
            .with_context(
                default_project_id=task.project_id.id,
                default_company_id=task.company_id.id,
                default_agile_item_type_id=self.configuration.id,
            )
            .create({"name": "Native defaulted client work"})
        )
        self.assertEqual(len(quick.agile_environment_status_ids), 4)
        with self.assertRaises(AccessError):
            task.write({"agile_tracks_environments": False})
        with self.assertRaises(AccessError):
            self.env["project.task"].with_user(self.member).with_context(
                default_agile_tracks_environments=True
            ).create({"name": "Forged tracking", "project_id": task.project_id.id})
        with self.assertRaises(AccessError):
            self.environments[0].with_user(self.member).write({"name": "Forged"})
        with self.assertRaises(AccessError):
            self.env["project.agile.environment"].with_user(self.member).create(
                {"name": "Forged", "project_id": task.project_id.id}
            )
        for values in (
            {"actor_id": self.manager.id},
            {"changed_at": "2000-01-01"},
            {"write_uid": self.manager.id},
            {"write_date": "2000-01-01"},
        ):
            with self.assertRaises(AccessError):
                line.with_user(self.member).write(values)
        with self.assertRaises(ValidationError):
            line.write(
                {
                    "environment_id": self.tasks[1]
                    .agile_environment_status_ids[0]
                    .environment_id.id
                }
            )
        status_model = self.env["project.task.environment.status"].with_user(
            self.member
        )
        foreign = self.projects[1].agile_environment_ids[0]
        with self.assertRaises(ValidationError):
            status_model.create({"task_id": task.id, "environment_id": foreign.id})
        with self.assertRaises(AccessError):
            status_model.with_context(default_actor_id=self.manager.id).create(
                {"task_id": task.id, "environment_id": foreign.id}
            )
        with self.assertRaises(ValidationError):
            self.environments[0].write({"project_id": self.projects[1].id})

    def test_custom_task_rules_company_and_backfill_atomic_rejection(self):
        hidden = self.tasks[0]
        line = hidden.agile_environment_status_ids[0]
        self.env["ir.rule"].create(
            {
                "name": "Hide one client task",
                "model_id": self.env.ref("project.model_project_task").id,
                "domain_force": repr([("id", "!=", hidden.id)]),
            }
        )
        status_model = self.env["project.task.environment.status"].with_user(
            self.member
        )
        self.assertNotIn(line, status_model.search([]))
        with self.assertRaises(AccessError):
            line.with_user(self.member).read(["status"])
        with self.assertRaises(AccessError):
            line.with_user(self.member).write({"status": "done"})
        before = self.projects[0].agile_environment_ids
        with self.assertRaises(AccessError):
            self.env["project.agile.environment"].with_user(self.manager).create(
                {"name": "Cannot omit hidden work", "project_id": self.projects[0].id}
            )
        self.assertEqual(self.projects[0].agile_environment_ids, before)
        other_company = self.env["res.company"].create(
            {"name": "Other environment company"}
        )
        foreign_project = (
            self.env["project.project"]
            .with_company(other_company)
            .create(
                {
                    "name": "Foreign",
                    "company_id": other_company.id,
                    "agile_enabled": True,
                    "agile_key": "ENVFOREIGN",
                    "privacy_visibility": "employees",
                }
            )
        )
        foreign = (
            self.env["project.agile.environment"]
            .with_company(other_company)
            .create({"name": "UAT", "project_id": foreign_project.id})
        )
        self.assertNotIn(
            foreign,
            self.env["project.agile.environment"].with_user(self.member).search([]),
        )
        with self.assertRaises(AccessError):
            status_model.create(
                {"task_id": self.tasks[1].id, "environment_id": foreign.id}
            )

    def test_enable_shared_type_and_existing_project(self):
        custom_type = self.env["project.agile.item.type"].create(
            {"name": "Client setup", "code": "client_setup", "uses_story_points": False}
        )
        task = self.tasks[0].copy({"agile_item_type_id": custom_type.id})
        archived = task.copy({"active": False})
        closed = task.copy({"state": "1_done"}) | task.copy({"state": "1_canceled"})
        self.assertFalse(task.agile_environment_status_ids)
        custom_type.with_context(active_test=False).write({"tracks_environments": True})
        self.assertEqual(len(task.agile_environment_status_ids), 4)
        self.assertFalse((closed | archived).agile_environment_status_ids)
        history = task.agile_environment_status_ids
        history[0].with_user(self.member).write({"status": "done"})
        snapshot = history.read(["status", "actor_id", "changed_at"])
        custom_type.write({"tracks_environments": False})
        self.assertFalse(any(task.agile_environment_status_ids.mapped("applicable")))
        custom_type.with_context(active_test=False).write({"tracks_environments": True})
        self.assertEqual(history.read(["status", "actor_id", "changed_at"]), snapshot)
        self.assertEqual(task.agile_environment_status_ids, history)
        self.assertFalse((closed | archived).agile_environment_status_ids)
        archived.with_user(self.member).write({"active": True})
        self.assertEqual(len(archived.agile_environment_status_ids), 4)
        project = self.env["project.project"].create(
            {"name": "Enable existing", "agile_key": "ENVENABLE"}
        )
        existing = self.env["project.task"].create(
            {
                "name": "Existing import",
                "project_id": project.id,
                "agile_item_type_id": self.data_import.id,
            }
        )
        project.write(
            {
                "agile_enabled": True,
                "agile_environment_ids": [Command.create({"name": "Staging"})],
            }
        )
        self.assertEqual(len(existing.agile_environment_status_ids), 1)

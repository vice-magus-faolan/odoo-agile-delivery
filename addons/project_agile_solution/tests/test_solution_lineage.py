"""Native nonadmin boundaries and reproducible, explicitly synthetic fixture seeds."""

import json
from pathlib import Path

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestSolutionLineage(TransactionCase):
    """Root proves identity and authority only, not downstream requirements/approval."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": "SYNTHETIC Other Company"}
        )
        cls.manager = mail_new_test_user(
            cls.env,
            "solution_manager",
            groups="project.group_project_manager",
            company_id=cls.company.id,
            company_ids=[Command.set((cls.company | cls.other_company).ids)],
        )
        cls.user = mail_new_test_user(
            cls.env,
            "solution_user",
            groups="project.group_project_user,base.group_allow_export",
            company_id=cls.company.id,
            company_ids=[Command.set(cls.company.ids)],
        )
        cls.portal = mail_new_test_user(
            cls.env, "solution_portal", groups="base.group_portal"
        )
        cls.project = cls._project("Visible", "SYNA", cls.company)
        cls.hidden = cls._project("Private", "SYNH", cls.company, privacy="followers")
        cls.foreign = cls._project("Other company", "SYNB", cls.other_company)
        cls.solution = (
            cls.env["project.agile.solution"]
            .with_user(cls.manager)
            .create({"name": "SYNTHETIC Lineage", "project_id": cls.project.id})
        )
        cls.hidden_solution = cls.env["project.agile.solution"].create(
            {"name": "SYNTHETIC Private Lineage", "project_id": cls.hidden.id}
        )
        cls.foreign_solution = cls.env["project.agile.solution"].create(
            {"name": "SYNTHETIC Foreign Lineage", "project_id": cls.foreign.id}
        )

    @classmethod
    def _project(cls, name, key, company, privacy="employees"):
        return cls.env["project.project"].create(
            {
                "name": "SYNTHETIC " + name,
                "agile_enabled": True,
                "agile_key": key,
                "company_id": company.id,
                "privacy_visibility": privacy,
            }
        )

    def test_current_project_visibility_applies_to_read_search_and_export(self):
        self.solution.with_user(self.user).read(["name"])
        self.assertEqual(
            self.solution.with_user(self.user).export_data(["name"])["datas"],
            [[self.solution.name]],
        )
        visible = self.env["project.agile.solution"].with_user(self.user).search([])
        self.assertIn(self.solution, visible)
        for hidden in (self.hidden_solution, self.foreign_solution):
            self.assertNotIn(hidden, visible)
            lineages = self.env["project.agile.solution"].with_user(self.user)
            domain = [("id", "=", hidden.id)]
            self.assertEqual(lineages.search_count(domain), 0)
            self.assertEqual(
                lineages._read_group(domain, ["project_id"], ["__count"]), []
            )
            self.assertEqual(lineages.name_search(hidden.name), [])
            with self.assertRaises(AccessError):
                hidden.with_user(self.user).read(["name"])
            with self.assertRaises(AccessError):
                hidden.with_user(self.user).export_data(["name"])
        with self.assertRaises(AccessError):
            self.solution.with_user(self.portal).read(["name"])

    def test_user_read_does_not_grant_lineage_create_write_or_delete(self):
        with self.assertRaises(AccessError):
            self.env["project.agile.solution"].with_user(self.user).create(
                {"name": "Unauthorized", "project_id": self.project.id}
            )
        with self.assertRaises(AccessError):
            self.solution.with_user(self.user).write({"name": "Unauthorized"})
        with self.assertRaises(AccessError):
            self.solution.with_user(self.user).unlink()

    def test_custom_project_rule_is_authoritative_even_for_manager(self):
        manager_solution = self.solution.with_user(self.manager)
        self.assertIn(manager_solution, manager_solution.search([]))
        manager_solution.read(["name"])
        rule = self.env["ir.rule"].create(
            {
                "name": "SYNTHETIC deny exact Project",
                "model_id": self.env.ref("project.model_project_project").id,
                "domain_force": repr([("id", "!=", self.project.id)]),
            }
        )
        self.assertNotIn(manager_solution, manager_solution.search([]))
        with self.assertRaises(AccessError):
            manager_solution.read(["name"])
        with self.assertRaises(AccessError):
            manager_solution.write({"name": "Bypassed"})
        with self.assertRaises(AccessError):
            manager_solution.create({"name": "Bypassed", "project_id": self.project.id})
        rule.unlink()
        self.assertIn(manager_solution, manager_solution.search([]))
        manager_solution.read(["name"])

    def test_company_and_context_are_not_authority(self):
        manager = self.manager
        manager.write({"company_ids": [Command.set(self.company.ids)]})
        lineage = self.env["project.agile.solution"].with_user(manager)
        self.assertNotIn(self.foreign_solution, lineage.search([]))
        before = self.env["project.agile.solution"].search_count([])
        for context in (
            {},
            {"allowed_company_ids": self.other_company.ids},
            {"solution_trusted": True, "sudo": True},
        ):
            with self.assertRaises(AccessError):
                lineage.with_context(**context).create(
                    {"name": "Forged", "project_id": self.foreign.id}
                )
        self.assertEqual(before, self.env["project.agile.solution"].search_count([]))
        with self.assertRaises(ValidationError):
            lineage.create(
                {
                    "name": "Forged company",
                    "project_id": self.project.id,
                    "company_id": self.other_company.id,
                }
            )

    def test_identity_scope_survives_rename_archive_and_rejects_moves(self):
        identity = self.solution.id
        self.solution.with_user(self.manager).write(
            {"name": "SYNTHETIC Renamed", "active": False}
        )
        self.assertEqual(self.solution.id, identity)
        self.assertEqual(self.solution.company_id, self.company)
        self.solution.with_user(self.user).read(["name"])
        with self.assertRaises(ValidationError):
            self.solution.with_user(self.manager).write({"project_id": self.foreign.id})
        with self.assertRaises(ValidationError):
            self.solution.write({"company_id": self.other_company.id})

    def test_ordinary_or_archived_projects_cannot_create_lineages(self):
        ordinary = self.env["project.project"].create({"name": "Ordinary"})
        for project in (ordinary, self.project):
            if project == self.project:
                project.active = False
            with self.assertRaises(ValidationError):
                self.env["project.agile.solution"].create(
                    {"name": "Invalid", "project_id": project.id}
                )

    def test_multi_create_failure_has_no_partial_lineage(self):
        before = self.env["project.agile.solution"].search_count([])
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["project.agile.solution"].with_user(self.manager).create(
                [
                    {"name": "Would be valid", "project_id": self.project.id},
                    {"name": "Invalid", "project_id": True},
                ]
            )
        self.assertEqual(before, self.env["project.agile.solution"].search_count([]))

    def test_enabled_companies_do_not_override_selected_company_scope(self):
        lineage = self.env["project.agile.solution"].with_user(self.manager)
        only_primary = lineage.with_context(allowed_company_ids=self.company.ids)
        self.assertNotIn(self.foreign_solution, only_primary.search([]))
        with self.assertRaises(AccessError):
            self.foreign_solution.with_env(only_primary.env).read(["name"])
        both = lineage.with_context(
            allowed_company_ids=(self.company | self.other_company).ids
        )
        self.assertIn(self.foreign_solution, both.search([]))
        self.foreign_solution.with_env(both.env).read(["name"])

    def test_unavailable_or_malformed_project_ids_are_rejected(self):
        lineage = self.env["project.agile.solution"].with_user(self.manager)
        for project_id in (False, True, 0, -1, "1", 999999999):
            with self.assertRaises(ValidationError):
                lineage.create({"name": "Invalid", "project_id": project_id})

    def test_companyless_native_project_and_unused_deletion(self):
        project = self._project("Shared", "SYNSHARED", self.env["res.company"])
        lineage = (
            self.env["project.agile.solution"]
            .with_user(self.manager)
            .create(
                {
                    "name": "SYNTHETIC shared initiative",
                    "project_id": project.id,
                }
            )
        )
        self.assertFalse(lineage.company_id)
        lineage.with_user(self.user).read(["name"])
        lineage.unlink()
        self.assertFalse(lineage.exists())

    def test_all_synthetic_scenarios_seed_existing_native_tasks_only(self):
        data = json.loads(
            (
                Path(__file__).parent / "fixtures" / "synthetic_scenarios.json"
            ).read_text()
        )
        self.assertTrue(data["synthetic"])
        self.assertEqual(
            {item["id"] for item in data["scenarios"]},
            {"portal", "integration", "internal"},
        )
        for scenario in data["scenarios"]:
            project = self._project(
                scenario["project_name"], scenario["project_key"], self.company
            )
            lineage = (
                self.env["project.agile.solution"]
                .with_user(self.manager)
                .create(
                    {
                        "name": scenario["project_name"],
                        "project_id": project.id,
                    }
                )
            )
            tasks = (
                self.env["project.task"]
                .with_user(self.user)
                .create(
                    [
                        {
                            "name": task["name"],
                            "description": task.get("manual_description", False),
                            "project_id": project.id,
                            "agile_item_type_id": self.env.ref(
                                "project_agile.project_agile_item_type_"
                                + task["item_type"]
                            ).id,
                        }
                        for task in scenario["tasks"]
                    ]
                )
            )
            self.assertEqual(tasks.project_id, lineage.project_id)
            self.assertTrue(all(tasks.mapped("agile_key")))
            self.assertEqual(len(tasks), len(scenario["tasks"]))
            for task, source in zip(tasks, scenario["tasks"], strict=False):
                if source.get("manual_description"):
                    self.assertIn(source["manual_description"], task.description)
                self.assertEqual(task.state, "01_in_progress")
                self.assertEqual(task.agile_story_points, 0)
            self.assertTrue(scenario["weaknesses"])
            # Contract expectation data is not fabricated runtime acceptance.
            self.assertNotIn("requirement_ids", lineage._fields)
        self.assertTrue(self.env.ref("project_agile_solution.action_solution_lineage"))

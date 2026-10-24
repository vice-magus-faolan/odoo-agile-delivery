from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestTaskActors(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ba = mail_new_test_user(
            cls.env, "actor_ba", groups="project_agile_solution.group_business_analyst"
        )
        cls.member = mail_new_test_user(
            cls.env, "actor_member", groups="project_agile.group_agile_member"
        )
        cls.manager = mail_new_test_user(
            cls.env, "actor_manager", groups="project.group_project_manager"
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Actor client",
                "agile_enabled": True,
                "agile_key": "ACTOR",
                "privacy_visibility": "employees",
            }
        )
        cls.other = cls.env["project.project"].create(
            {
                "name": "Other client",
                "agile_enabled": True,
                "agile_key": "OTHERACTOR",
                "privacy_visibility": "employees",
            }
        )
        cls.solution = (
            cls.env["project.agile.solution"]
            .with_user(cls.ba)
            .create({"name": "Solution A", "project_id": cls.project.id})
        )
        second = (
            cls.env["project.agile.solution"]
            .with_user(cls.ba)
            .create({"name": "Solution B", "project_id": cls.project.id})
        )
        foreign = cls.env["project.agile.solution"].create(
            {"name": "Other Solution", "project_id": cls.other.id}
        )
        cls.actors = (
            cls.env["project.agile.solution.context"]
            .with_user(cls.ba)
            .create(
                [
                    {"name": "Buyer", "kind": "actor", "solution_id": cls.solution.id},
                    {"name": "Planner", "kind": "actor", "solution_id": second.id},
                ]
            )
        )
        cls.foreign_actor = (
            cls.env["project.agile.solution.context"]
            .with_user(cls.ba)
            .create(
                {"name": "Foreign Actor", "kind": "actor", "solution_id": foreign.id}
            )
        )
        cls.domain = (
            cls.env["project.agile.solution.context"]
            .with_user(cls.ba)
            .create(
                {
                    "name": "Not an Actor",
                    "kind": "domain",
                    "solution_id": cls.solution.id,
                }
            )
        )
        cls.tasks = cls.env["project.task"].with_user(cls.ba)
        cls.story = cls.env.ref("project_agile.project_agile_item_type_story")

    def _create(self, **values):
        return self.tasks.create(
            {
                "name": "People served",
                "project_id": self.project.id,
                "agile_item_type_id": self.story.id,
                **values,
            }
        )

    def test_ba_multiple_actors_form_and_non_story(self):
        self.assertFalse(self.ba.has_group("project.group_project_manager"))
        with Form(self.tasks.with_context(default_project_id=self.project.id)) as form:
            form.name = "BA entry"
            form.agile_item_type_id = self.story
            form.solution_actor_ids.add(self.actors[0])
            form.solution_actor_ids.add(self.actors[1])
        work = form.record
        self.assertEqual(work.solution_actor_ids, self.actors)
        self.assertEqual(
            work.solution_actor_ids.mapped("display_name"), ["Buyer", "Planner"]
        )
        work.agile_item_type_id = self.env.ref(
            "project_agile.project_agile_item_type_task"
        )
        self.assertEqual(work.solution_actor_ids, self.actors)
        work.write({"solution_actor_ids": [Command.clear()]})
        self.assertFalse(work.solution_actor_ids)
        self.assertFalse(self._create().solution_actor_ids)

    def test_rpc_scope_commands_and_no_mutation(self):
        work = self._create(solution_actor_ids=[Command.set(self.actors.ids)])
        for actor in (self.foreign_actor, self.domain):
            with self.assertRaises(ValidationError):
                work.write(
                    {
                        "name": "Must rollback",
                        "solution_actor_ids": [Command.link(actor.id)],
                    }
                )
            self.assertEqual(work.name, "People served")
            self.assertEqual(work.solution_actor_ids, self.actors)
            with self.assertRaises(ValidationError):
                self._create(solution_actor_ids=[Command.set(actor.ids)])
        for command in (
            Command.create({"name": "Injected"}),
            Command.update(self.actors[0].id, {"name": "Changed"}),
            Command.delete(self.actors[0].id),
        ):
            with self.assertRaises(ValidationError):
                work.write({"solution_actor_ids": [command]})
        self.assertEqual(self.actors[0].name, "Buyer")
        with self.assertRaises(ValidationError):
            self.tasks.with_context(
                default_solution_actor_ids=[Command.set(self.domain.ids)]
            ).create({"name": "Forged default", "project_id": self.project.id})

    def test_caller_record_and_company_authority(self):
        work = self._create()
        with self.assertRaises(AccessError):
            work.with_user(self.member).write(
                {"solution_actor_ids": [Command.set(self.actors.ids)]}
            )
        rule = self.env["ir.rule"].create(
            {
                "name": "Hidden Actor",
                "model_id": self.env["ir.model"]._get_id(
                    "project.agile.solution.context"
                ),
                "domain_force": repr([("id", "!=", self.actors[0].id)]),
            }
        )
        with self.assertRaises(AccessError):
            work.write({"solution_actor_ids": [Command.set(self.actors.ids)]})
        rule.unlink()
        company = self.env["res.company"].create({"name": "Foreign company"})
        project = self.env["project.project"].create(
            {
                "name": "Foreign company Project",
                "company_id": company.id,
                "agile_enabled": True,
                "agile_key": "FOREIGNACTOR",
            }
        )
        self.manager.company_ids = [Command.link(company.id)]
        solution = (
            self.env["project.agile.solution"]
            .with_user(self.manager)
            .with_company(company)
            .create({"name": "Foreign company Solution", "project_id": project.id})
        )
        actor = (
            self.env["project.agile.solution.context"]
            .with_user(self.manager)
            .with_company(company)
            .create(
                {"name": "Company Actor", "kind": "actor", "solution_id": solution.id}
            )
        )
        with self.assertRaises(AccessError):
            work.write({"solution_actor_ids": [Command.link(actor.id)]})
        self.assertFalse(work.solution_actor_ids)
        self.ba.company_ids = [Command.link(company.id)]
        with self.assertRaises(ValidationError):
            work.with_context(
                allowed_company_ids=[self.env.company.id, company.id]
            ).write({"solution_actor_ids": [Command.link(actor.id)]})
        self.assertFalse(work.solution_actor_ids)

    def test_same_project_copy_and_project_template_copy(self):
        work = self._create(solution_actor_ids=[Command.set(self.actors.ids)])
        self.assertEqual(work.copy().solution_actor_ids, self.actors)
        self.assertFalse(work.copy({"project_id": self.other.id}).solution_actor_ids)
        child = self._create(
            agile_item_type_id=self.env.ref(
                "project_agile.project_agile_item_type_task"
            ).id,
            parent_id=work.id,
            solution_actor_ids=[Command.set(self.actors.ids)],
        )
        copied = self.project.with_user(self.manager).copy()
        self.assertTrue(copied.task_ids)
        self.assertFalse(copied.task_ids.solution_actor_ids)
        self.project.is_template = True
        restored = self.project.with_user(self.manager).action_create_from_template()
        self.assertTrue(restored.task_ids)
        self.assertFalse(restored.task_ids.solution_actor_ids)
        self.assertEqual(child.solution_actor_ids, self.actors)
        self.assertEqual(work.solution_actor_ids, self.actors)

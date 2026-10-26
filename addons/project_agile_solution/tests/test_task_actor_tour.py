from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestTaskActorTour(HttpCase):
    def _acceptance_setup(self):
        analyst = mail_new_test_user(
            self.env,
            "task_acceptance_author",
            groups="project_agile_solution.group_business_analyst",
        )
        member = mail_new_test_user(
            self.env,
            "task_acceptance_reader",
            groups="project_agile.group_agile_member",
        )
        project = self.env["project.project"].create(
            {
                "name": "Dispatch acceptance",
                "agile_enabled": True,
                "agile_key": "DISPATCH",
                "privacy_visibility": "employees",
            }
        )
        solution = (
            self.env["project.agile.solution"]
            .with_user(analyst)
            .create({"name": "Dispatch", "project_id": project.id})
        )
        revisions = self.env["project.agile.requirement.revision"].with_user(analyst)
        for title in (
            "Buyer dispatch",
            "Receipt check",
            "Hidden agreement",
            "Retired agreement",
        ):
            identity = (
                self.env["project.agile.requirement"]
                .with_user(analyst)
                .create({"name": title, "solution_id": solution.id})
            )
            revisions |= revisions.create(
                {
                    "requirement_id": identity.id,
                    "title": title,
                    "description": "Client dispatch workflow",
                    "rationale": "Avoid lost dispatches",
                    "verification_method": "Manual check for " + title,
                    "acceptance_expectations": "Given a buyer\n"
                    "When dispatch is approved\nThen record " + title,
                }
            )
        return analyst, member, project, solution, revisions

    def test_native_task_exact_acceptance_hides_forbidden_and_retired_links(self):
        analyst, member, project, _solution, revisions = self._acceptance_setup()
        task = (
            self.env["project.task"]
            .with_user(analyst)
            .create({"name": "Check dispatch", "project_id": project.id})
        )
        links = (
            self.env["project.agile.requirement.task.link"]
            .with_user(analyst)
            .create(
                [
                    {"task_id": task.id, "requirement_revision_id": row.id}
                    for row in revisions
                ]
            )
        )
        links[-1].action_retire("Replaced acceptance")
        successor = revisions.browse(
            revisions[0].requirement_id.action_new_revision()["res_id"]
        )
        successor.write({"title": "Unlinked new agreement"})
        self.env["ir.rule"].create(
            {
                "name": "Hidden task-side agreement",
                "model_id": self.env["ir.model"]._get_id(revisions._name),
                "domain_force": repr([("id", "!=", revisions[2].id)]),
            }
        )
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Dispatch work",
                "res_model": "project.task",
                "view_mode": "form",
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}/{task.id}",
            "solution_task_exact_acceptance",
            login=member.login,
        )
        links[1].action_retire("Receipt moved to separate work")
        self.start_tour(
            f"/odoo/action-{action.id}/{task.id}",
            "solution_task_retired_acceptance",
            login=member.login,
        )

    def test_native_creation_choice_preview_and_saved_criteria(self):
        analyst, _member, project, solution, revisions = self._acceptance_setup()
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Explicit dispatch creation",
                "res_model": "project.agile.solution.task.intent",
                "view_mode": "form",
                "context": repr(
                    {
                        "default_solution_id": solution.id,
                        "default_operation": "create",
                        "default_name": "Explicit dispatch work",
                        "default_requirement_revision_ids": [(6, 0, revisions[:2].ids)],
                        "default_agile_item_type_id": self.env.ref(
                            "project_agile.project_agile_item_type_task"
                        ).id,
                    }
                ),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}/new",
            "solution_task_explicit_criteria_copy",
            login=analyst.login,
        )
        intent = (
            self.env["project.agile.solution.task.intent"]
            .with_user(analyst)
            .search([("name", "=", "Explicit dispatch work")])
        )
        self.assertEqual(len(intent), 1)
        self.assertTrue(intent.copy_acceptance_expectations)
        self.assertEqual(intent.state, "consumed")
        self.assertEqual(intent.task_id.project_id, project)
        self.assertEqual(
            intent.task_id.agile_acceptance_criteria, intent.acceptance_criteria_preview
        )

    def test_native_new_pristine_story_switch_and_saved_description(self):
        analyst, _member, project, _solution, _revisions = self._acceptance_setup()
        story = self.env.ref("project_agile.project_agile_item_type_story")
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "New client work",
                "res_model": "project.task",
                "view_mode": "form",
                "context": repr(
                    {
                        "default_project_id": project.id,
                        "default_name": "Pristine Story switched to Task",
                        "default_agile_item_type_id": story.id,
                    }
                ),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}/new",
            "solution_task_pristine_story_switch",
            login=analyst.login,
        )
        switched = (
            self.env["project.task"]
            .with_user(analyst)
            .search(
                [
                    ("name", "=", "Pristine Story switched to Task"),
                    ("project_id", "=", project.id),
                ]
            )
        )
        self.assertEqual(len(switched), 1)
        self.assertFalse(switched.description)
        self.assertEqual(switched.agile_item_type_id.code, "task")
        saved = (
            self.env["project.task"]
            .with_user(analyst)
            .create(
                {
                    "name": "Saved client wording",
                    "project_id": project.id,
                    "agile_item_type_id": story.id,
                    "description": "<p>Keep authored client wording</p>",
                }
            )
        )
        self.start_tour(
            f"/odoo/action-{action.id}/{saved.id}",
            "solution_task_saved_story_switch",
            login=analyst.login,
        )
        saved.invalidate_recordset(["description"])
        self.assertEqual(saved.description, "<p>Keep authored client wording</p>")

    def test_native_board_and_backlog_names(self):
        user = mail_new_test_user(
            self.env,
            "actor_board_ba",
            groups="project_agile_solution.group_business_analyst",
        )
        project = self.env["project.project"].create(
            {
                "name": "Actor board",
                "agile_enabled": True,
                "agile_key": "ACTORBOARD",
                "privacy_visibility": "employees",
            }
        )
        solution = (
            self.env["project.agile.solution"]
            .with_user(user)
            .create({"name": "Board Solution", "project_id": project.id})
        )
        actors = (
            self.env["project.agile.solution.context"]
            .with_user(user)
            .create(
                [
                    {"name": name, "kind": "actor", "solution_id": solution.id}
                    for name in ("Buyer", "Planner")
                ]
            )
        )
        self.env["project.task.type"].create(
            {"name": "Ready", "project_ids": [Command.set(project.ids)]}
        )
        tasks = self.env["project.task"].with_user(user)
        tasks.create(
            {
                "name": "Actor Story",
                "project_id": project.id,
                "agile_item_type_id": self.env.ref(
                    "project_agile.project_agile_item_type_story"
                ).id,
                "solution_actor_ids": [Command.set(actors.ids)],
            }
        )
        tasks.create({"name": "Empty Task", "project_id": project.id})
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Actor backlog board",
                "res_model": "project.task",
                "view_mode": "kanban,list,form",
                "domain": repr([("project_id", "=", project.id)]),
                "context": repr({"default_project_id": project.id}),
                "view_ids": [
                    Command.create(
                        {
                            "sequence": 1,
                            "view_mode": "kanban",
                            "view_id": self.env.ref("project.view_task_kanban").id,
                        }
                    ),
                    Command.create(
                        {
                            "sequence": 2,
                            "view_mode": "list",
                            "view_id": self.env.ref(
                                "project_agile.view_task_list_agile_backlog"
                            ).id,
                        }
                    ),
                ],
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}", "solution_task_actor_names", login=user.login
        )

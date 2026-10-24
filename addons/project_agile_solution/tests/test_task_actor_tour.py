from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestTaskActorTour(HttpCase):
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

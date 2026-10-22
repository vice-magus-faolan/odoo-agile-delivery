from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestEnvironmentTour(HttpCase):
    def test_native_environment_status_edit_and_history(self):
        user = mail_new_test_user(
            self.env, "environment_tour_user", groups="project_agile.group_agile_member"
        )
        project = self.env["project.project"].create(
            {
                "name": "Environment tour client",
                "agile_enabled": True,
                "agile_key": "ENVTOUR",
                "privacy_visibility": "employees",
            }
        )
        self.env["project.agile.environment"].create(
            [
                {
                    "name": name,
                    "project_id": project.id,
                    "sequence": index * 10,
                    "is_production": name == "Production",
                }
                for index, name in enumerate(("E2E", "UAT", "Production"))
            ]
        )
        task = (
            self.env["project.task"]
            .with_user(user)
            .create(
                {
                    "name": "Import client vendors",
                    "project_id": project.id,
                    "agile_item_type_id": self.env.ref(
                        "project_agile.project_agile_item_type_data_import"
                    ).id,
                }
            )
        )
        pending = task.copy({"name": "Awaiting production"})
        complete = task.copy({"name": "Complete in both"})
        (pending | complete).agile_environment_status_ids.filtered(
            lambda line: line.environment_id.name == "UAT"
        ).write({"status": "verified"})
        complete.agile_environment_status_ids.filtered(
            lambda line: line.environment_id.is_production
        ).write({"status": "done"})
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Client work",
                "res_model": "project.task",
                "view_mode": "list,form",
                "view_id": self.env.ref("project.open_view_all_tasks_list_view").id,
                "search_view_id": self.env.ref(
                    "project_agile.view_task_search_agile"
                ).id,
                "domain": repr([("project_id", "=", project.id)]),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}/{task.id}",
            "agile_environment_status",
            login=user.login,
        )
        task.invalidate_recordset()
        lines = task.agile_environment_status_ids
        production = lines.filtered(lambda line: line.environment_id.is_production)
        self.assertEqual(production.status, "done")
        self.assertEqual(production.actor_id, user)
        self.assertTrue(production.changed_at)
        self.assertEqual(
            lines.filtered(lambda line: line.environment_id.name == "UAT").status,
            "todo",
        )
        self.start_tour(
            f"/odoo/action-{action.id}",
            "agile_environment_gap_search",
            login=user.login,
        )

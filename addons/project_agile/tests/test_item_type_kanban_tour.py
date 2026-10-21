from lxml import etree

from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestItemTypeKanbanTour(HttpCase):
    def test_native_single_mixed_and_business_type_columns(self):
        user = mail_new_test_user(
            self.env, "mixed_board_user", groups="project_agile.group_agile_member"
        )
        self.assertFalse(user.has_group("project.group_project_manager"))
        project = self.env["project.project"].create(
            {
                "name": "Client mixed board",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "BOARD",
            }
        )
        story = self.env.ref("project_agile.project_agile_item_type_story")
        configuration = self.env.ref(
            "project_agile.project_agile_item_type_configuration"
        )
        for name, item_type in (
            ("Code review", story),
            ("Waiting on client", configuration),
            ("Shared empty", False),
        ):
            self.env["project.task.type"].create(
                {
                    "name": name,
                    "project_ids": [Command.set(project.ids)],
                    "agile_item_type_ids": [
                        Command.set(item_type.ids if item_type else [])
                    ],
                }
            )
        tasks = self.env["project.task"].with_user(user)
        for name, item_type in (
            ("Add approval", story),
            ("Configure taxes", configuration),
        ):
            tasks.create(
                {
                    "name": name,
                    "project_id": project.id,
                    "agile_item_type_id": item_type.id,
                }
            )
        # Native search facets OR selections in the same section. Numeric IDs
        # distinguish this contract from filtering task names or copied core JS.
        search = etree.Element("search")
        for name, label, item_type in (
            ("development", "Development work", story),
            ("business", "Business work", configuration),
        ):
            etree.SubElement(
                search,
                "filter",
                name=name,
                string=label,
                domain=repr([("agile_item_type_id", "=", item_type.id)]),
            )
        view = self.env["ir.ui.view"].create(
            {
                "name": "Mixed board test search",
                "model": "project.task",
                "arch": etree.tostring(search, encoding="unicode"),
            }
        )
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Mixed client board",
                "res_model": "project.task",
                "view_mode": "kanban,list,form",
                "search_view_id": view.id,
                "domain": repr([("project_id", "=", project.id)]),
                "context": repr(
                    {"default_project_id": project.id, "project_kanban": True}
                ),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}", "agile_mixed_type_columns", login=user.login
        )
        # Use a valid Task-to-Story conversion, outside the board journey's
        # item-type/column expectations, through the native conversion dialog.
        task = tasks.create(
            {
                "name": "Implement approval",
                "project_id": project.id,
                "agile_item_type_id": self.env.ref(
                    "project_agile.project_agile_item_type_task"
                ).id,
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}/{task.id}",
            "agile_task_key_parent_picker",
            login=user.login,
        )
        task.invalidate_recordset(["parent_id"])
        self.assertEqual(task.parent_id.agile_key, "BOARD-1")

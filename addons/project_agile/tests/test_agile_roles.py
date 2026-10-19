from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestAgileRoles(TransactionCase):
    def test_member_assignment_and_project_configuration_boundary(self):
        member = mail_new_test_user(
            self.env, "agile_role_member", groups="project_agile.group_agile_member"
        )
        self.assertTrue(member.has_group("project.group_project_user"))
        self.assertFalse(member.has_group("project.group_project_manager"))
        group = self.env.ref("project_agile.group_agile_member")
        hierarchy = self.env["res.groups"]._get_view_group_hierarchy()
        privilege = self.env.ref("project.res_groups_privilege_project")
        self.assertEqual(hierarchy["groups"][group.id]["privilege_id"], privilege.id)
        self.assertIn(group.id, hierarchy["privileges"][privilege.id]["group_ids"])
        # Native group assignment preserves the implied-group closure.
        member.write({"group_ids": [Command.unlink(group.id)]})
        self.assertFalse(member.has_group("project_agile.group_agile_member"))
        member.write({"group_ids": [Command.link(group.id)]})
        self.assertTrue(member.has_group("project_agile.group_agile_member"))
        project = self.env["project.project"].create(
            {
                "name": "Roles",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "ROLES",
                "agile_estimation_method": "fibonacci",
            }
        )
        caller = project.with_user(member)
        with self.assertRaises(AccessError):
            caller.write({"name": "No new native Project write authority"})
        # Isolate the field boundary from native model ACL denial: another
        # addon may legitimately grant Project writes, but never Agile setup.
        self.env["ir.model.access"].create(
            {
                "name": "Role test native Project write extension",
                "model_id": self.env.ref("project.model_project_project").id,
                "group_id": group.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": False,
            }
        )
        self.assertFalse(member.has_group("project.group_project_manager"))
        caller.write({"name": "Ordinary permitted Project rename"})
        ordinary = caller.create({"name": "Ordinary permitted Project"})
        self.assertFalse(ordinary.agile_enabled)
        for values in (
            {"agile_enabled": False},
            {"agile_key": "FORGED"},
            {"agile_estimation_method": "none"},
            {"agile_default_item_type_id": False},
        ):
            for record in (caller, caller.sudo()):
                with self.assertRaises(AccessError):
                    record.write(values)
        with self.assertRaises(AccessError):
            caller.create({"name": "Forged", "agile_key": "FORGED"})
        with self.assertRaises(AccessError):
            caller.with_context(default_agile_enabled=True).create({"name": "Forged"})
        task = (
            self.env["project.task"]
            .with_user(member)
            .create(
                {
                    "name": "Typed work",
                    "project_id": project.id,
                    "agile_item_type_id": self.env.ref(
                        "project_agile.project_agile_item_type_story"
                    ).id,
                    "agile_story_points": 5,
                }
            )
        )
        task.write({"agile_story_points": 8})
        self.assertEqual(task.agile_story_points, 8)
        types = self.env["project.agile.item.type"].with_user(member)
        with self.assertRaises(AccessError):
            types.create({"name": "Forbidden", "code": "forbidden_role"})
        with self.assertRaises(AccessError):
            task.agile_item_type_id.write({"name": "Forbidden"})
        member.write(
            {
                "group_ids": [
                    Command.link(self.env.ref("project.group_project_manager").id)
                ]
            }
        )
        caller.write({"agile_estimation_method": "none"})
        self.assertTrue(member.has_group("project.group_project_manager"))

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
            for record in (caller, caller.with_context(sudo=True)):
                with self.assertRaises(AccessError):
                    record.write(values)
        for record in (caller, caller.with_context(sudo=True)):
            with self.assertRaises(AccessError):
                record.create({"name": "Forged", "agile_key": "FORGED"})
            with self.assertRaises(AccessError):
                record.with_context(default_agile_enabled=True).create(
                    {"name": "Forged"}
                )
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

    def test_non_admin_sudo_plain_project_copy(self):
        user = mail_new_test_user(
            self.env, "agile_sudo_copy_user", groups="project.group_project_user"
        )
        self.assertFalse(user.has_group("project.group_project_manager"))
        self.assertFalse(user.has_group("base.group_system"))
        project = self.env["project.project"].create(
            {"name": "Plain template", "privacy_visibility": "employees"}
        )
        caller = project.with_user(user)
        self.assertFalse(caller.env.su)
        with self.assertRaises(AccessError):
            caller.write({"name": "No native Project write authority"})
        trusted = caller.sudo()
        self.assertTrue(trusted.env.su)
        self.assertEqual(trusted.env.uid, user.id)
        # Native copies carry defaulted Agile fields even for plain Projects.
        copied = trusted.copy()
        self.assertNotEqual(copied.id, project.id)
        self.assertTrue(copied.name)
        self.assertEqual(copied.privacy_visibility, project.privacy_visibility)
        self.assertEqual(copied.company_id, project.company_id)
        self.assertFalse(copied.agile_enabled)
        self.assertFalse(copied.agile_key)
        self.assertEqual(copied.agile_estimation_method, "none")
        self.assertEqual(
            copied.agile_default_item_type_id, project.agile_default_item_type_id
        )
        copied.write({"agile_estimation_method": "fibonacci"})
        self.assertEqual(copied.agile_estimation_method, "fibonacci")
        copied.write({"agile_enabled": True, "agile_key": "TRUSTEDENABLE"})
        self.assertEqual(
            copied.agile_default_item_type_id,
            self.env.ref("project_agile.project_agile_item_type_task"),
        )


class TestAgileProjectSharing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal = mail_new_test_user(
            cls.env, "agile_sharing_portal", groups="base.group_portal"
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Native shared Project",
                "privacy_visibility": "portal",
                "partner_id": cls.portal.partner_id.id,
            }
        )
        cls.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": cls.project.id,
                "collaborator_ids": [
                    Command.create(
                        {"partner_id": cls.portal.partner_id.id, "access_mode": "edit"}
                    )
                ],
            }
        )
        cls.task = cls.env["project.task"].create(
            {"name": "Shared work", "project_id": cls.project.id}
        )

    def test_native_portal_create_and_field_isolation(self):
        caller = self.env["project.task"].with_user(self.portal)
        self.assertFalse(caller.env.su)
        task = caller.with_context(default_project_id=self.project.id).create(
            {"name": "Portal-authored work"}
        )
        self.assertEqual(task.project_id, self.project)
        self.assertEqual(task.display_name, "Portal-authored work")
        self.assertFalse(task.with_user(self.env.user).agile_key)
        task.write({"name": "Portal-owned title"})
        for values in (
            {"project_id": self.project.id},
            {"agile_story_points": 5},
            {"agile_acceptance_criteria": "Internal metadata"},
        ):
            with self.assertRaises(AccessError):
                task.with_context(project_sharing_create=True).write(values)
        with self.assertRaises(AccessError):
            caller.with_context(default_project_id=self.project.id).create(
                {"name": "Forged", "agile_key": "FORGED-1"}
            )

    def test_keyed_labels_preserve_portal_field_security(self):
        self.project.write({"agile_enabled": True, "agile_key": "SHARED"})
        self.assertTrue(self.task.agile_key)
        self.assertIn(self.task.agile_key, self.task.display_name)
        caller = self.task.with_user(self.portal)
        self.assertEqual(caller.display_name, self.task.name)
        for field in (
            "agile_key",
            "agile_story_points",
            "agile_environment_status_ids",
        ):
            with self.assertRaises(AccessError):
                caller.read([field])

    def test_unshared_client_project_and_company_remain_hidden(self):
        outsider = mail_new_test_user(
            self.env, "agile_sharing_outsider", groups="base.group_portal"
        )
        with self.assertRaises(AccessError):
            self.task.with_user(outsider).read(["name"])
        other_company = self.env["res.company"].create({"name": "Unshared company"})
        project = self.env["project.project"].create(
            {
                "name": "Unshared foreign Project",
                "privacy_visibility": "invited_users",
                "company_id": other_company.id,
            }
        )
        hidden = self.env["project.task"].create(
            {"name": "Foreign work", "project_id": project.id}
        )
        with self.assertRaises(AccessError):
            hidden.with_user(self.portal).read(["display_name"])
        with self.assertRaises(AccessError):
            self.env["project.task"].with_user(self.portal).with_context(
                default_project_id=project.id
            ).create({"name": "Foreign forged work"})

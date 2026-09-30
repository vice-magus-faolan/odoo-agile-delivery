"""Finite rules and two-person authority through real nonadmin ORM boundaries."""

from unittest.mock import patch

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGitPolicyRules(TransactionCase):
    def setUp(self):
        super().setUp()
        capability = "project_agile_git_automation.group_git_policy_manager"
        self.author = mail_new_test_user(self.env, "policy_author", groups=capability)
        self.approver = mail_new_test_user(self.env, "policy_approver", groups=capability)
        self.manager = mail_new_test_user(self.env, "policy_plain_manager", groups="project.group_project_manager")
        self.executor = mail_new_test_user(self.env, "policy_executor", groups="project.group_project_user")
        self.project = self.env["project.project"].create({
            "name": "Finite policy", "company_id": self.env.company.id,
            "agile_enabled": True, "agile_key": "FIN", "privacy_visibility": "employees",
        })
        self.repository = self.env["project.git.repository"].create({
            "name": "Finite", "provider": "github", "provider_repository_id": "finite",
            "canonical_url": "https://github.com/synthetic/finite", "project_id": self.project.id,
        })
        self.stages = self.env["project.task.type"].create([
            {"name": name, "project_ids": [Command.link(self.project.id)]}
            for name in ("Develop", "Review", "QA")
        ])
        self.task = self.env["project.task"].create({
            "name": "Policy target", "project_id": self.project.id, "stage_id": self.stages[0].id,
        })
        self.rule = self.env["project.git.policy.rule"].with_user(self.author).create({
            "name": "Merged to QA", "repository_id": self.repository.id,
        })
        self.revision_values = {
            "rule_id": self.rule.id, "target_branch": "main",
            "allowed_source_stage_ids": [Command.set(self.stages[:2].ids)],
            "target_stage_id": self.stages[2].id, "execution_user_id": self.executor.id,
        }
        self.revision = self.env["project.git.policy.revision"].with_user(self.author).create(self.revision_values)

    def _activate(self):
        self.project.with_user(self.author).action_enable_git_policy()
        return self._approve(self.revision)

    def _approve(self, revision):
        result = revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)
        return self.env["project.git.policy.activation"].browse(result["activation_id"])

    def _new_revision(self, revision=None):
        revision = revision if revision is not None else self.revision
        result = revision.action_new_revision()
        return revision.browse(result["res_id"])

    def _assert_revoked(self, activation):
        self.assertFalse(activation._validate_current_authority())
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)

    def test_disabled_dry_run_defaults_and_no_members_seeded(self):
        self.assertFalse(self.project.git_policy_enabled)
        self.assertEqual(self.project.git_policy_mode, "dry_run")
        self.assertEqual(self.project.git_policy_authority_epoch, 0)
        self.assertFalse(self.rule.activation_id)
        self.assertEqual(self.revision.trigger, "merged_pull_request")
        self.assertEqual(self.revision.effect, "task_stage_transition")
        self.assertFalse(self.env["ir.cron"].search([("model_id.model", "like", "project.git.policy.%")]))

    def test_company_scope_and_serial_revision_are_server_derived(self):
        self.assertEqual(self.rule.owner_id, self.author)
        self.assertEqual(self.revision.company_id, self.project.company_id)
        second = self.env["project.git.policy.revision"].with_user(self.author).create(self.revision_values)
        self.assertEqual((self.revision.revision, second.revision), (1, 2))
        for key in ("company_id", "project_id", "owner_id", "revision", "approver_id", "approved_at"):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                self.env["project.git.policy.revision"].with_user(self.author).create({**self.revision_values, key: 1})

    def test_stage_and_check_bounds_are_enforced_on_create_and_write(self):
        other_project = self.env["project.project"].create({"name": "Other", "company_id": self.env.company.id})
        foreign = self.env["project.task.type"].create({"name": "Foreign", "project_ids": [Command.link(other_project.id)]})
        invalid = (
            {"allowed_source_stage_ids": [Command.clear()]},
            {"target_stage_id": self.stages[0].id},
            {"target_stage_id": foreign.id},
            {"allowed_source_stage_ids": [Command.set(foreign.ids)]},
            {"target_branch": "*"}, {"target_branch": " "}, {"target_branch": "x" * 256},
            {"trigger": "push"}, {"effect": "complete_task"},
            {"expression": "True"}, {"model": "project.task"}, {"method": "write"},
            {"field": "state"}, {"domain": []}, {"mode": "apply"},
            {"required_check_ids": [Command.create({"name": "*"})]},
            {"required_check_ids": [Command.create({"name": "CI"}), Command.create({"name": "CI"})]},
            {"required_check_ids": [Command.create({"name": str(i)}) for i in range(21)]},
        )
        for patch in invalid:
            expected = ValueError if {"trigger", "effect"}.intersection(patch) else ValidationError
            with self.subTest(patch=patch), self.env.cr.savepoint(), self.assertRaises(expected):
                self.env["project.git.policy.revision"].with_user(self.author).create({**self.revision_values, **patch})
            with self.subTest(write=patch), self.env.cr.savepoint(), self.assertRaises(expected):
                self.revision.write(patch)
        stages = self.env["project.task.type"].create([
            {"name": str(i), "project_ids": [Command.link(self.project.id)]} for i in range(21)
        ])
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.revision.write({"allowed_source_stage_ids": [Command.set(stages.ids)]})
        self.revision.write({"required_check_ids": [Command.create({"name": "CI / Linux"})]})
        self.assertEqual(self.revision.required_check_ids.name, "CI / Linux")
        check = self.revision.required_check_ids
        with self.assertRaises(ValidationError):
            check.write({"revision_id": 999999})

    def test_default_context_cannot_mint_controls_or_identity(self):
        context = {
            "default_company_id": 1, "default_owner_id": 1, "default_approver_id": 1,
            "default_approved_at": "2020-01-01", "default_activation_id": 1,
            "default_git_policy_enabled": True, "default_git_policy_mode": "apply",
            "policy_trusted": True, "policy_execution_user_id": 1,
        }
        rule = self.env["project.git.policy.rule"].with_user(self.author).with_context(context).create({
            "name": "Safe", "repository_id": self.repository.id,
        })
        revision = self.env["project.git.policy.revision"].with_user(self.author).with_context(context).create({
            **self.revision_values, "rule_id": rule.id,
        })
        self.assertEqual(rule.owner_id, self.author)
        self.assertFalse(rule.activation_id)
        self.assertFalse(revision.approver_id)
        self.assertEqual(revision.execution_user_id, self.executor)
        project = self.env["project.project"].with_context(context).create({"name": "Defaults"})
        self.assertFalse(project.git_policy_enabled)
        self.assertEqual(project.git_policy_mode, "dry_run")

    def test_policy_relations_cannot_edit_native_stages(self):
        for command in (
            Command.update(self.stages[0].id, {"name": "Unauthorized nested edit"}),
            Command.create({"name": "Nested stage", "project_ids": [Command.link(self.project.id)]}),
            Command.delete(self.stages[1].id),
        ):
            with self.subTest(command=command), self.env.cr.savepoint(), self.assertRaises(ValidationError):
                self.revision.write({"allowed_source_stage_ids": [command]})
        self.assertEqual(self.stages[0].name, "Develop")
        self.assertEqual(self.task.stage_id, self.stages[0])

    def test_plain_manager_and_project_user_cannot_configure_or_activate(self):
        for user in (self.manager, self.executor):
            with self.subTest(user=user.login):
                with self.assertRaises(AccessError):
                    self.env["project.git.policy.rule"].with_user(user).create({"name": "Denied", "repository_id": self.repository.id})
                for method in ("action_enable_git_policy", "action_disable_git_policy"):
                    with self.assertRaises(AccessError):
                        getattr(self.project.with_user(user), method)()
                with self.assertRaises(AccessError):
                    self.revision.with_user(user).action_activate(acknowledge_native_side_effects=True)
                with self.assertRaises(AccessError):
                    self.rule.with_user(user).action_disable()
                with self.assertRaises(AccessError):
                    self.rule.with_user(user).action_transfer_owner(self.approver.id)
                with self.assertRaises(AccessError):
                    self.revision.with_user(user).action_new_revision()
                with self.assertRaises(AccessError):
                    self.revision.with_user(user).write({"target_branch": "release"})

    def test_raw_control_activation_and_history_writes_are_denied(self):
        for values in ({"git_policy_enabled": True}, {"git_policy_mode": "apply"}, {"git_policy_authority_epoch": 2}):
            with self.assertRaises(ValidationError):
                self.project.with_user(self.author).write(values)
        for values in ({"owner_id": self.approver.id}, {"activation_id": 1}, {"repository_id": self.repository.id}):
            with self.assertRaises(ValidationError):
                self.rule.write(values)
        for model in ("project.git.policy.activation", "project.git.policy.revocation"):
            with self.assertRaises(AccessError):
                self.env[model].with_user(self.approver).with_context(policy_trusted=True).create({})
        with self.assertRaises(ValidationError):
            self.project.with_user(self.author).action_enable_git_policy(mode="eval")

    def test_two_person_approval_acknowledgment_and_actual_task_authority(self):
        with self.assertRaises(ValidationError):
            self.revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)
        self.project.with_user(self.author).action_enable_git_policy()
        with self.assertRaises(AccessError):
            self.revision.action_activate(acknowledge_native_side_effects=True)
        with self.assertRaises(ValidationError):
            self.revision.with_user(self.approver).action_activate()
        activation = self._approve(self.revision)
        self.assertTrue(activation._validate_current_authority(self.task))
        self.assertEqual(activation.execution_user_id, self.executor)
        self.assertEqual(activation.approver_id, self.approver)
        self.assertEqual(activation.mode, "dry_run")
        self.assertEqual(self.rule.active_revision_id, self.revision)
        self.assertEqual(self.task.stage_id, self.stages[0])
        self.assertEqual(self.task.state, "01_in_progress")
        for record in (activation, self.revision):
            with self.assertRaises(ValidationError):
                record.write({"execution_user_id": self.author.id})
            with self.assertRaises(ValidationError):
                record.unlink()

    def test_activation_rechecks_rule_archival_after_control_lock(self):
        self.project.with_user(self.author).action_enable_git_policy()
        original_lock = type(self.rule)._lock_control
        archived = False

        def lock_then_archive(rule):
            nonlocal archived
            original_lock(rule)
            if not archived:
                archived = True
                rule.with_user(self.author).write({"active": False})

        # Exercise the public boundary with a control change at the fence, not a
        # claimed independent-connection race (covered by the later worker lane).
        with patch.object(type(self.rule), "_lock_control", lock_then_archive):
            with self.assertRaises(ValidationError):
                self._approve(self.revision)
        self.assertFalse(self.rule.activation_id)
        self.assertFalse(self.revision.approved_at)

    def test_executor_uid_one_portal_inactive_and_foreign_company_denied(self):
        portal = mail_new_test_user(self.env, "policy_portal", groups="base.group_portal")
        inactive = mail_new_test_user(self.env, "policy_inactive", groups="project.group_project_user")
        inactive.active = False
        self.project.with_user(self.author).action_enable_git_policy()
        for identity in (self.env.ref("base.user_root"), portal, inactive):
            with self.subTest(identity=identity.id), self.env.cr.savepoint(), self.assertRaises(AccessError):
                self.revision.write({"execution_user_id": identity.id})
                self.revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)

    def test_custom_task_rule_denial_is_not_model_acl_authority(self):
        self.env["ir.rule"].create({
            "name": "Deny exact policy Task", "model_id": self.env["ir.model"]._get("project.task").id,
            "domain_force": "[('name', '!=', 'Policy target')]",
        })
        self.env["project.task"].with_user(self.executor).browse().check_access("write")
        with self.assertRaises(AccessError):
            self.task.with_user(self.executor).check_access("write")
        self.project.with_user(self.author).action_enable_git_policy()
        with self.assertRaises(AccessError):
            self.revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)
        self.assertFalse(self.rule.activation_id)

    def test_custom_project_denial_and_forged_record_ids(self):
        self.env["ir.rule"].create({
            "name": "Deny policy Project", "model_id": self.env["ir.model"]._get("project.project").id,
            "domain_force": "[('name', '!=', 'Finite policy')]",
        })
        with self.assertRaises(AccessError):
            self.rule.write({"name": "Denied"})
        with self.assertRaises(AccessError):
            self.revision.action_new_revision()
        with self.assertRaises(AccessError):
            self.project.with_user(self.author).action_enable_git_policy()
        with self.assertRaises(AccessError):
            self.rule.action_transfer_owner(self.approver.id)

    def test_revision_replacement_has_new_cutoff_and_never_replays_old_epoch(self):
        first = self._activate()
        revised = self._new_revision()
        self._assert_revoked(first)
        self.assertFalse(revised.approved_at)
        revised.write({"target_branch": "release"})
        next_activation = self._approve(revised)
        self.assertNotEqual(first, next_activation)
        self.assertGreaterEqual(next_activation.activated_at, first.activated_at)
        self.assertGreater(next_activation.authority_epoch, first.authority_epoch)
        self.assertFalse(first._validate_current_authority())
        with self.assertRaises(ValidationError):
            self.revision.with_user(self.approver).action_activate(acknowledge_native_side_effects=True)

    def test_disable_reenable_and_mode_change_are_fresh_explicit_epochs(self):
        first = self._activate()
        self.project.with_user(self.author).action_disable_git_policy()
        self._assert_revoked(first)
        self.project.with_user(self.author).action_enable_git_policy(mode="apply")
        self.assertFalse(self.rule.activation_id)
        revised = self._new_revision()
        second = self._approve(revised)
        self.assertEqual(second.mode, "apply")
        self.assertNotEqual(first, second)
        self.assertFalse(first._validate_current_authority())
        self.assertEqual(self.task.stage_id, self.stages[0])

    def test_owner_transfer_archive_and_delete_cannot_reuse_identity(self):
        first = self._activate()
        self.rule.action_transfer_owner(self.approver.id)
        self._assert_revoked(first)
        with self.assertRaises(AccessError):
            self.revision.action_new_revision()
        revised = self._new_revision(self.revision.with_user(self.approver))
        self.assertEqual(revised.owner_id, self.approver)
        self.rule.with_user(self.approver).write({"active": False})
        with self.assertRaises(ValidationError):
            self.rule.with_user(self.approver).write({"active": True})
        with self.assertRaises(ValidationError):
            self.rule.with_user(self.approver).unlink()
        self.assertTrue(first.exists())

    def test_identity_inactivation_group_company_revocation_never_resurrects(self):
        for field, value in (
            ("active", False),
            ("group_ids", [Command.clear(), Command.link(self.env.ref("base.group_user").id)]),
        ):
            with self.subTest(field=field), self.assertRaises(_RollbackSubcase), self.env.cr.savepoint():
                first = self._activate()
                self.executor.write({field: value})
                self._assert_revoked(first)
                self.executor.active = True
                self.executor.group_ids = [Command.link(self.env.ref("project.group_project_user").id)]
                self.assertFalse(first._validate_current_authority())
                # Roll back this subcase without rolling back the testcase fixture.
                raise _RollbackSubcase()

    def test_security_rule_revocation_stage_changes_and_repository_archive(self):
        activation = self._activate()
        self.env["ir.rule"].create({
            "name": "Authority changed", "model_id": self.env["ir.model"]._get("project.task").id,
            "domain_force": "[(1, '=', 1)]",
        })
        self._assert_revoked(activation)
        revised = self._new_revision()
        activation = self._approve(revised)
        self.stages[2].write({"project_ids": [Command.clear()]})
        self._assert_revoked(activation)
        self.stages[2].write({"project_ids": [Command.link(self.project.id)]})
        self.assertFalse(activation._validate_current_authority())
        revised = self._new_revision(revised)
        activation = self._approve(revised)
        self.repository.active = False
        self._assert_revoked(activation)
        self.repository.active = True
        self.assertFalse(activation._validate_current_authority())

    def test_stage_notifications_and_personal_stages_are_rejected(self):
        self.stages[2].rating_active = True
        with self.assertRaises(ValidationError):
            self._activate()
        self.stages[2].rating_active = False
        self.stages[2].project_ids = [Command.clear()]
        with self.assertRaises(ValidationError):
            self._activate()

    def test_repository_identity_and_history_are_not_repurposable(self):
        activation = self._activate()
        with self.assertRaises(ValidationError):
            self.repository.write({"provider_repository_id": "recycled"})
        with self.env.cr.savepoint(), self.assertRaises(Exception):
            self.repository.unlink()
        self.assertTrue(activation.exists())

    def test_multiple_enabled_companies_and_reassignment_invalidate_history(self):
        company = self.env["res.company"].create({"name": "Finite second company"})
        for user in (self.author, self.approver, self.executor):
            user.company_ids = [Command.link(company.id)]
        activation = self._activate()
        context = {"allowed_company_ids": [self.env.company.id, company.id]}
        self.assertTrue(self.rule.with_context(context).has_access("read"))
        self.project.with_context(context).write({"company_id": company.id})
        self._assert_revoked(activation)
        self.assertEqual(activation.company_id, self.env.company)
        self.assertEqual(self.rule.company_id, self.env.company)
        with self.assertRaises(AccessError):
            self.revision.action_new_revision()

    def test_company_context_cannot_grant_scope_and_companyless_projects_stay_facts_only(self):
        company = self.env["res.company"].create({"name": "Forbidden company"})
        with self.assertRaises(AccessError):
            self.rule.with_context(allowed_company_ids=[company.id]).write({"name": "Forged"})
        self.project.company_id = False
        with self.assertRaises(AccessError):
            self.project.with_user(self.author).action_enable_git_policy()

    def test_public_form_and_wizard_require_fresh_approver_acknowledgment(self):
        self.project.with_user(self.author).action_enable_git_policy()
        for user in (self.executor, self.manager):
            with self.assertRaises(AccessError):
                self.revision.with_user(user).action_activate_from_form()
            with self.assertRaises(AccessError):
                self.env["project.git.policy.approval.wizard"].with_user(user).create({"revision_id": self.revision.id})
        action = self.revision.with_user(self.approver).with_context(
            default_acknowledge_native_side_effects=True, default_execution_user_id=1,
        ).action_activate_from_form()
        wizard = self.env[action["res_model"]].with_user(self.approver).browse(action["res_id"])
        self.assertFalse(wizard.acknowledge_native_side_effects)
        with self.assertRaises(ValidationError):
            wizard.action_approve()
        with self.assertRaises(ValidationError):
            wizard.write({"revision_id": self.revision.id})
        wizard.write({"acknowledge_native_side_effects": True})
        self.assertEqual(wizard.action_approve(), {"type": "ir.actions.act_window_close"})
        self.assertEqual(self.rule.activation_id.execution_user_id, self.executor)
        self.assertEqual(self.task.stage_id, self.stages[0])

    def test_activation_never_trusts_context_for_mode_identity_or_acknowledgment(self):
        self.project.with_user(self.author).action_enable_git_policy()
        context = {"policy_execution_user_id": 1, "default_execution_user_id": 1,
                   "git_policy_mode": "apply", "acknowledge_native_side_effects": True,
                   "policy_trusted": True, "force_company": 1}
        revision = self.revision.with_user(self.approver).with_context(context)
        with self.assertRaises(ValidationError):
            revision.action_activate()
        result = revision.action_activate(acknowledge_native_side_effects=True)
        activation = self.env["project.git.policy.activation"].browse(result["activation_id"])
        self.assertEqual(activation.execution_user_id, self.executor)
        self.assertEqual(activation.mode, "dry_run")
        self.assertEqual(activation.approver_id, self.approver)

    def test_emergency_system_administrator_can_disable_but_not_activate(self):
        system = mail_new_test_user(self.env, "policy_system", groups="base.group_system,project.group_project_manager")
        activation = self._activate()
        self.assertFalse(system.has_group("project_agile_git_automation.group_git_policy_manager"))
        self.rule.with_user(system).action_disable()
        self._assert_revoked(activation)
        self.project.with_user(system).action_disable_git_policy()
        with self.assertRaises(AccessError):
            self.project.with_user(system).action_enable_git_policy()
        with self.assertRaises(AccessError):
            self.revision.with_user(system).action_activate(acknowledge_native_side_effects=True)

    def test_private_project_and_custom_visibility_apply_to_every_policy_read_surface(self):
        self.project.privacy_visibility = "followers"
        for model, ids in (
            ("project.git.policy.rule", self.rule.ids),
            ("project.git.policy.revision", self.revision.ids),
        ):
            records = self.env[model].with_user(self.executor)
            self.assertEqual(records.search_count([("id", "in", ids)]), 0)
            self.assertFalse(records.search([("id", "in", ids)]))
            with self.assertRaises(AccessError):
                records.browse(ids).read(["project_id"])
        self.project.message_subscribe(partner_ids=self.executor.partner_id.ids)
        self.assertTrue(self.rule.with_user(self.executor).has_access("read"))
        deny = self.env["ir.rule"].create({
            "name": "Hide Project from policy reads", "model_id": self.env["ir.model"]._get("project.project").id,
            "domain_force": "[('name', '!=', 'Finite policy')]",
        })
        self.assertFalse(self.rule.with_user(self.executor).search([("id", "=", self.rule.id)]))
        deny.unlink()
        self.assertTrue(self.rule.with_user(self.executor).has_access("read"))

    def test_delete_request_archives_and_revokes_without_losing_history(self):
        activation = self._activate()
        self.rule.unlink()
        self.assertTrue(self.rule.exists())
        self.assertFalse(self.rule.active)
        self._assert_revoked(activation)
        revocation = activation.revocation_ids
        for history in (activation, revocation):
            with self.assertRaises(ValidationError):
                history.sudo().write({})
            with self.assertRaises(ValidationError):
                history.sudo().unlink()
        with self.assertRaises(AccessError):
            self.revision.sudo().write({})
        with self.assertRaises(ValidationError):
            self.revision.sudo().unlink()
        for model in ("project.git.policy.activation", "project.git.policy.revocation"):
            with self.assertRaises(AccessError):
                self.env[model].sudo().create({})

    def test_company_membership_revocation_and_restoration_are_terminal(self):
        other_company = self.env["res.company"].create({"name": "Executor alternate company"})
        self.executor.company_ids = [Command.link(other_company.id)]
        activation = self._activate()
        self.executor.write({"company_id": other_company.id, "company_ids": [Command.set(other_company.ids)]})
        self._assert_revoked(activation)
        self.executor.company_ids = [Command.link(self.env.company.id)]
        self.assertFalse(activation._validate_current_authority())

    def test_removed_capability_and_acl_changes_do_not_restore_approval(self):
        activation = self._activate()
        self.author.group_ids = [Command.unlink(self.env.ref("project_agile_git_automation.group_git_policy_manager").id)]
        self._assert_revoked(activation)
        self.author.group_ids = [Command.link(self.env.ref("project_agile_git_automation.group_git_policy_manager").id)]
        self.assertFalse(activation._validate_current_authority())
        revision = self._new_revision()
        activation = self._approve(revision)
        acl = self.env["ir.model.access"].create({
            "name": "Synthetic Task authority", "model_id": self.env["ir.model"]._get("project.task").id,
            "group_id": self.env.ref("project.group_project_user").id, "perm_read": True,
        })
        self._assert_revoked(activation)
        revision = self._new_revision(revision)
        activation = self._approve(revision)
        acl.write({"perm_write": True})
        self._assert_revoked(activation)
        revision = self._new_revision(revision)
        activation = self._approve(revision)
        acl.unlink()
        self._assert_revoked(activation)

    def test_unlinked_source_stages_and_stage_notifications_revoke_even_after_restoration(self):
        activation = self._activate()
        self.stages[0].project_ids = [Command.clear()]
        self._assert_revoked(activation)
        self.stages[0].project_ids = [Command.link(self.project.id)]
        self.assertFalse(activation._validate_current_authority())
        revision = self._new_revision()
        activation = self._approve(revision)
        self.stages[2].rating_active = True
        self._assert_revoked(activation)
        self.stages[2].rating_active = False
        self.assertFalse(activation._validate_current_authority())

    def test_multiple_rules_have_independent_epochs_for_future_conflict_detection(self):
        first = self._activate()
        rule = self.env["project.git.policy.rule"].with_user(self.author).create({
            "name": "Second explicit rule", "repository_id": self.repository.id,
        })
        revision = self.env["project.git.policy.revision"].with_user(self.author).create({
            **self.revision_values, "rule_id": rule.id,
        })
        second = self._approve(revision)
        self.assertTrue(first._validate_current_authority())
        self.assertTrue(second._validate_current_authority())
        self.project.with_user(self.author).action_disable_git_policy()
        self.assertFalse(first._validate_current_authority())
        self.assertFalse(second._validate_current_authority())

    def test_project_and_task_unfollow_restore_cannot_resurrect_approval(self):
        for record in (self.project, self.task):
            with self.subTest(model=record._name), self.assertRaises(_RollbackSubcase), self.env.cr.savepoint():
                self.project.privacy_visibility = "followers"
                self.project.message_subscribe(partner_ids=self.executor.partner_id.ids)
                self.task.message_subscribe(partner_ids=self.executor.partner_id.ids)
                activation = self._activate()
                record.with_user(self.author).message_unsubscribe(partner_ids=self.executor.partner_id.ids)
                # Restore before validation: revocation must be a durable native
                # mutation hook, not dependent on catching a temporary denial.
                record.message_subscribe(partner_ids=self.executor.partner_id.ids)
                self.assertTrue(activation.revocation_ids)
                self.assertFalse(activation._validate_current_authority())
                raise _RollbackSubcase()

    def test_follower_reassignment_revokes_original_project_authority(self):
        self.project.message_subscribe(partner_ids=self.executor.partner_id.ids)
        activation = self._activate()
        follower = self.env["mail.followers"].search([
            ("res_model", "=", "project.project"), ("res_id", "=", self.project.id),
            ("partner_id", "=", self.executor.partner_id.id),
        ])
        partner = self.env["res.partner"].create({"name": "Synthetic replacement follower"})
        follower.write({"partner_id": partner.id})
        follower.write({"partner_id": self.executor.partner_id.id})
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(activation._validate_current_authority())

    def test_all_policy_read_surfaces_and_public_controls_reject_hidden_project(self):
        self.executor.group_ids = [Command.link(self.env.ref("base.group_allow_export").id)]
        self.revision.write({"required_check_ids": [Command.create({"name": "CI"})]})
        activation = self._activate()
        self.project.privacy_visibility = "followers"
        records = (self.rule, self.revision, self.revision.required_check_ids,
                   activation, activation.revocation_ids)
        for record in records:
            with self.subTest(model=record._name):
                model = record.with_user(self.executor).browse()
                domain = [("id", "in", record.ids)]
                model.check_access("read")
                self.assertFalse(model.search(domain))
                self.assertEqual(model.search_count(domain), 0)
                self.assertEqual(model._read_group(domain, [], ["__count"])[0][0], 0)
                with self.assertRaises(AccessError):
                    record.with_user(self.executor).read(["project_id"])
                with self.assertRaises(AccessError):
                    record.with_user(self.executor).export_data(["project_id"])

        self.env["ir.rule"].create({
            "name": "Hide configured Project even from capability holders",
            "model_id": self.env["ir.model"]._get("project.project").id,
            "domain_force": "[('id', '!=', %d)]" % self.project.id,
        })
        calls = (
            (self.rule, "action_disable", {}),
            (self.rule, "action_transfer_owner", {"new_owner_id": self.approver.id}),
            (self.rule, "unlink", {}),
            (self.revision, "action_new_revision", {}),
            (self.revision, "action_activate_from_form", {}),
            (self.revision.with_user(self.approver), "action_activate", {"acknowledge_native_side_effects": True}),
            (self.project.with_user(self.author), "action_enable_git_policy", {}),
            (self.project.with_user(self.author), "action_disable_git_policy", {}),
        )
        for record, method, kwargs in calls:
            with self.subTest(method=method), self.assertRaises(AccessError):
                getattr(record, method)(**kwargs)
        with self.assertRaises(AccessError):
            self.env["project.git.policy.approval.wizard"].with_user(self.approver).create({"revision_id": self.revision.id})

    def test_required_checks_and_revision_batch_create_cannot_mutate_approved_history(self):
        self.revision.write({"required_check_ids": [Command.create({"name": "CI"})]})
        activation = self._activate()
        check = self.revision.required_check_ids
        for method, values in (("write", {"name": "Other CI"}), ("unlink", None)):
            with self.assertRaises(ValidationError):
                getattr(check, method)(values) if values is not None else check.unlink()
        with self.assertRaises(ValidationError):
            self.env["project.git.policy.required.check"].with_user(self.author).create({"revision_id": self.revision.id, "name": "Extra"})
        self.assertTrue(activation._validate_current_authority())
        revisions = self.env["project.git.policy.revision"].with_user(self.author).create([
            self.revision_values, self.revision_values,
        ])
        self.assertEqual(revisions.mapped("revision"), [2, 3])
        self._assert_revoked(activation)


class _RollbackSubcase(Exception):
    """Internal testcase savepoint rollback marker."""

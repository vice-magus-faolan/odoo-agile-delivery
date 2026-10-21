"""Finite rules and two-person authority through real nonadmin ORM boundaries."""

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestGitPolicyRules(TransactionCase):
    def setUp(self):
        super().setUp()
        capability = "project_agile_git_automation.group_git_policy_manager"
        self.author = mail_new_test_user(self.env, "policy_author", groups=capability)
        self.approver = mail_new_test_user(
            self.env, "policy_approver", groups=capability
        )
        self.manager = mail_new_test_user(
            self.env, "policy_plain_manager", groups="project.group_project_manager"
        )
        self.executor = mail_new_test_user(
            self.env, "policy_executor", groups="project.group_project_user"
        )
        self.project = self.env["project.project"].create(
            {
                "name": "Finite policy",
                "company_id": self.env.company.id,
                "agile_enabled": True,
                "agile_key": "FIN",
                "privacy_visibility": "employees",
            }
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "Finite",
                "provider": "github",
                "provider_repository_id": "finite",
                "canonical_url": "https://github.com/synthetic/finite",
                "project_id": self.project.id,
            }
        )
        self.stages = self.env["project.task.type"].create(
            [
                {"name": name, "project_ids": [Command.link(self.project.id)]}
                for name in ("Develop", "Review", "QA")
            ]
        )
        self.task = self.env["project.task"].create(
            {
                "name": "Policy target",
                "project_id": self.project.id,
                "stage_id": self.stages[0].id,
            }
        )
        self.rule = (
            self.env["project.git.policy.rule"]
            .with_user(self.author)
            .create(
                {
                    "name": "Merged to QA",
                    "repository_id": self.repository.id,
                }
            )
        )
        self.revision_values = {
            "rule_id": self.rule.id,
            "target_branch": "main",
            "allowed_source_stage_ids": [Command.set(self.stages[:2].ids)],
            "target_stage_id": self.stages[2].id,
            "execution_user_id": self.executor.id,
        }
        self.revision = (
            self.env["project.git.policy.revision"]
            .with_user(self.author)
            .create(self.revision_values)
        )

    def _activate(self):
        self.project.with_user(self.author).action_enable_git_policy()
        return self._approve(self.revision)

    def _approve(self, revision):
        result = (
            revision.with_user(self.approver)
            .with_context(allowed_company_ids=revision.company_id.ids)
            .action_activate(acknowledge_native_side_effects=True)
        )
        return self.env["project.git.policy.activation"].browse(result["activation_id"])

    def _new_revision(self, revision=None):
        revision = revision if revision is not None else self.revision
        result = revision.action_new_revision()
        return revision.browse(result["res_id"])

    def _assert_revoked(self, activation):
        self.assertFalse(activation._validate_current_authority())
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)

    def test_inverse_project_stage_removal_restore_is_terminal(self):
        for stage in (self.stages[0], self.stages[2]):
            with (
                self.subTest(stage=stage.name),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                activation = self._activate()
                self.project.with_user(self.author).write(
                    {"type_ids": [Command.unlink(stage.id)]}
                )
                self.assertNotIn(self.project, stage.project_ids)
                self.project.with_user(self.author).write(
                    {"type_ids": [Command.link(stage.id)]}
                )
                self.assertTrue(activation.revocation_ids)
                self.assertFalse(self.rule.activation_id)
                self.assertFalse(activation._validate_current_authority())
                raise _RollbackSubcase()

    def test_new_project_shared_stage_relation_revokes_existing_epoch(self):
        activation = self._activate()
        project = (
            self.env["project.project"]
            .with_user(self.author)
            .create(
                {
                    "name": "New shared-stage Project",
                    "company_id": self.env.company.id,
                    "type_ids": [Command.link(self.stages[2].id)],
                }
            )
        )
        self.assertIn(project, self.stages[2].project_ids)
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        project.write({"type_ids": [Command.clear()]})
        self.assertFalse(activation._validate_current_authority())

    def test_native_personal_stage_alias_assignment_mutations_revoke(self):
        # Native personal stages share project_task_user_rel with Task.user_ids;
        # mutations do not necessarily enter Task.write(user_ids=...).
        personal = (
            self.env["project.task.stage.personal"]
            .with_user(self.executor)
            .create(
                {
                    "task_id": self.task.id,
                    "user_id": self.executor.id,
                }
            )
        )
        self.task.invalidate_recordset(["user_ids"])
        self.assertIn(self.executor, self.task.user_ids)
        activation = self._activate()
        personal.unlink()
        self.task.invalidate_recordset(["user_ids"])
        self.assertNotIn(self.executor, self.task.user_ids)
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        personal = personal.create(
            {"task_id": self.task.id, "user_id": self.executor.id}
        )
        self.assertFalse(activation._validate_current_authority())
        activation = self._approve(self._new_revision())
        self.task.with_user(self.author).write(
            {"personal_stage_type_ids": [Command.clear()]}
        )
        self.assertTrue(activation.revocation_ids)
        # Clearing stages preserves the native assignee row when stage_id is NULL.
        personal.exists().unlink()
        other = (
            self.env["project.task"]
            .with_user(self.author)
            .create(
                {
                    "name": "Native alias reassignment",
                    "project_id": self.project.id,
                }
            )
        )
        successor = self._new_revision()
        activation = self._approve(successor)
        personal = personal.create(
            {"task_id": self.task.id, "user_id": self.executor.id}
        )
        self.assertTrue(activation.revocation_ids)
        activation = self._approve(self._new_revision(successor))
        with self.assertRaises(AccessError):
            personal.with_user(self.author).write({"task_id": other.id})
        self.assertFalse(activation.revocation_ids)
        with self.assertRaises(_RollbackSubcase), self.env.cr.savepoint():
            personal.write({"task_id": other.id})
            self.assertTrue(activation.revocation_ids)
            raise _RollbackSubcase()
        self.assertFalse(activation.revocation_ids)
        personal.write({"task_id": other.id})
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)

    def test_supported_name_denial_restore_is_terminal_without_validation(self):
        self.env["ir.rule"].create(
            {
                "name": "Literal Task authority",
                "model_id": self.env["ir.model"]._get("project.task").id,
                "domain_force": "[('name', '!=', 'Excluded')]",
            }
        )
        activation = self._activate()
        self.task.with_user(self.author).with_context(
            git_policy_skip_revocation=True
        ).write({"name": "Excluded"})
        with self.assertRaises(AccessError):
            self.task.with_user(self.executor).check_access("write")
        with self.assertRaises(AccessError):
            self.task.with_user(self.executor).check_access("read")
        self.task.write({"name": "Policy target"})
        self.task.with_user(self.executor).check_access("write")
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        self.assertFalse(activation._validate_current_authority())
        with self.assertRaises(ValidationError):
            self._approve(self.revision)
        successor = self._new_revision()
        fresh = self._approve(successor)
        self.assertNotEqual(activation, fresh)
        self.assertGreaterEqual(fresh.activated_at, activation.activated_at)
        self.assertTrue(fresh._validate_current_authority())

    def test_disabled_dry_run_defaults_and_no_members_seeded(self):
        self.assertFalse(self.project.git_policy_enabled)
        self.assertEqual(self.project.git_policy_mode, "dry_run")
        self.assertEqual(self.project.git_policy_authority_epoch, 0)
        self.assertFalse(self.rule.activation_id)
        self.assertEqual(self.revision.trigger, "merged_pull_request")
        self.assertEqual(self.revision.effect, "task_stage_transition")
        self.assertEqual(
            self.env["ir.cron"].search(
                [("model_id.model", "like", "project.git.policy.%")]
            ),
            self.env.ref("project_agile_git_automation.ir_cron_git_policy"),
        )
        self.assertFalse(self.env["project.git.policy.schedule"].search([]))
        self.assertFalse(self.env["project.git.policy.attempt"].search([]))
        self.assertFalse(self.env["project.git.policy.effect"].search([]))

    def test_all_native_stage_relation_directions_and_commands_are_terminal(self):
        for inverse in (False, True):
            for stage in (self.stages[0], self.stages[2]):
                for kind in (Command.UNLINK, Command.CLEAR, Command.SET):
                    with (
                        self.subTest(inverse=inverse, stage=stage.name, kind=kind),
                        self.assertRaises(_RollbackSubcase),
                        self.env.cr.savepoint(),
                    ):
                        activation = self._activate()
                        record, field = (
                            (self.project, "type_ids")
                            if inverse
                            else (stage, "project_ids")
                        )
                        removed_id = stage.id if inverse else self.project.id
                        command = {
                            Command.UNLINK: Command.unlink(removed_id),
                            Command.CLEAR: Command.clear(),
                            Command.SET: Command.set(
                                [i for i in record[field].ids if i != removed_id]
                            ),
                        }[kind]
                        record.with_user(self.author).write({field: [command]})
                        self.assertNotIn(self.project, stage.project_ids)
                        self.assertTrue(activation.revocation_ids)
                        self.assertFalse(self.rule.activation_id)
                        record.with_user(self.author).write(
                            {field: [Command.link(removed_id)]}
                        )
                        self.assertFalse(activation._validate_current_authority())
                        raise _RollbackSubcase()

    def test_native_rejects_time_expression_without_partial_revocation(self):
        activation = self._activate()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env["ir.rule"].create(
                {
                    "name": "Unsupported time expression",
                    "model_id": self.env["ir.model"]._get("project.task").id,
                    "domain_force": "[('name', '!=', time.strftime('%Y'))]",
                }
            )
        self.assertFalse(activation.revocation_ids)
        self.assertEqual(self.rule.activation_id, activation)

    def test_supported_active_denial_restore_is_terminal(self):
        self.env["ir.rule"].create(
            {
                "name": "Literal active Task authority",
                "model_id": self.env["ir.model"]._get("project.task").id,
                "domain_force": "[('active', '=', True)]",
            }
        )
        activation = self._activate()
        self.task.with_user(self.author).write({"active": False})
        with self.assertRaises(AccessError):
            self.task.with_user(self.executor).check_access("write")
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        self.task.write({"active": True})
        self.task.with_user(self.executor).check_access("write")
        self.assertFalse(activation._validate_current_authority())

    def test_supported_literal_boolean_combinations_leave_odoo_as_evaluator(self):
        for domain in (
            "[('name', '=', 'Policy target'), ('active', '!=', False)]",
            "['&', ('name', 'in', ['Policy target', 'Other']), "
            "('name', 'not in', ['Excluded'])]",
            "['|', ('active', '=', True), '!', ('name', '=', 'Excluded')]",
        ):
            with (
                self.subTest(domain=domain),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                self.env["ir.rule"].create(
                    {
                        "name": "Supported literal combinations",
                        "model_id": self.env["ir.model"]._get("project.task").id,
                        "domain_force": domain,
                    }
                )
                activation = self._activate()
                self.assertTrue(activation._validate_current_authority())
                self.assertEqual(self.task.stage_id, self.stages[0])
                raise _RollbackSubcase()

    def test_unsupported_custom_authority_inputs_refuse_activation(self):
        for domain in (
            "[('stage_id', '!=', False)]",
            "[('display_name', '!=', 'Excluded')]",
            "[('project_id.name', '!=', 'Excluded')]",
            "[('name', 'like', 'Policy')]",
            "[('name', '!=', user.name)]",
            "[(1, '=', 1)]",
        ):
            with (
                self.subTest(domain=domain),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                self.env["ir.rule"].create(
                    {
                        "name": "Unsupported Task profile",
                        "model_id": self.env["ir.model"]._get("project.task").id,
                        "domain_force": domain,
                    }
                )
                self.project.with_user(self.author).action_enable_git_policy()
                with self.assertRaisesRegex(AccessError, "unsupported"):
                    self._approve(self.revision)
                self.assertFalse(self.revision.approved_at)
                self.assertFalse(self.rule.activation_id)
                raise _RollbackSubcase()

    def test_unsupported_custom_project_repository_stage_identity_rules(self):
        for model in (
            "project.project",
            "project.git.repository",
            "project.task.type",
            "res.users",
        ):
            with (
                self.subTest(model=model),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                self.env["ir.rule"].create(
                    {
                        "name": "Unsupported other-model profile",
                        "model_id": self.env["ir.model"]._get(model).id,
                        "domain_force": "[(1, '=', 1)]",
                    }
                )
                self.project.with_user(self.author).action_enable_git_policy()
                with self.assertRaisesRegex(AccessError, "unsupported"):
                    self._approve(self.revision)
                raise _RollbackSubcase()

    def test_native_rule_drift_and_restoration_need_fresh_supported_approval(self):
        native = self.env.ref("project.task_comp_rule")
        old_domain = native.domain_force
        activation = self._activate()
        native.write({"domain_force": "[('company_id', 'in', company_ids)]"})
        self.assertTrue(activation.revocation_ids)
        successor = self._new_revision()
        with self.assertRaisesRegex(AccessError, "unsupported"):
            self._approve(successor)
        native.write({"domain_force": old_domain})
        self.assertFalse(activation._validate_current_authority())
        fresh = self._approve(successor)
        self.assertTrue(fresh._validate_current_authority())

    def test_native_profile_missing_inactive_group_and_permission_drift_rejected(self):
        native = self.env.ref("project.task_comp_rule")
        for values in (
            {"active": False},
            {"perm_write": False},
            {"groups": [Command.link(self.env.ref("base.group_user").id)]},
        ):
            with (
                self.subTest(values=values),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                native.write(values)
                self.project.with_user(self.author).action_enable_git_policy()
                with self.assertRaisesRegex(AccessError, "unsupported"):
                    self._approve(self.revision)
                raise _RollbackSubcase()

    def test_literal_field_metadata_drift_fails_closed(self):
        for name in ("name", "active"):
            with (
                self.subTest(field=name),
                patch.object(
                    self.env["project.task"]._fields[name], "company_dependent", True
                ),
            ):
                self.project.with_user(self.author).action_enable_git_policy()
                with self.assertRaisesRegex(AccessError, "unsupported"):
                    self._approve(self.revision)

    def test_literal_classifier_rejects_malformed_and_excessive_rule_data(self):
        from ..models.policy_authority_profile import _check_literal_domain

        for source in (
            "[]",
            "{}",
            "['|', ('active', '=', True)]",
            "[('name', '=', 3)]",
            "[('active', '=', 1)]",
            "[('name', 'in', 'Policy target')]",
            "[('name', 'in', [])]",
            "[('active', 'in', [True, 'False'])]",
            "[('name', '=', user.name)]",
            "[('name', '=', str(1))]",
            "[('name', '!=', time.strftime('%Y'))]",
            repr([("active", "=", True)] * 65),
            " " * 8193,
        ):
            with self.subTest(source=source[:80]), self.assertRaises(AccessError):
                _check_literal_domain(source)

    def test_native_group_relation_metadata_drift_refuses_approval(self):
        for name in ("implied_ids", "implied_by_ids", "rule_groups"):
            with (
                self.subTest(field=name),
                patch.object(
                    self.env["res.groups"]._fields[name], "company_dependent", True
                ),
            ):
                self.project.with_user(self.author).action_enable_git_policy()
                with self.assertRaisesRegex(AccessError, "unsupported"):
                    self._approve(self.revision)
                self.assertFalse(self.rule.activation_id)

    def test_task_create_unlink_and_bulk_edits_revoke_without_policy_business_writes(
        self,
    ):
        activation = self._activate()
        tasks = (
            self.env["project.task"]
            .with_user(self.author)
            .create(
                [
                    {"name": "Created A", "project_id": self.project.id},
                    {"name": "Created B", "project_id": self.project.id},
                ]
            )
        )
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        successor = self._new_revision()
        activation = self._approve(successor)
        tasks.write({"name": "Bulk normal edit"})
        self.assertTrue(activation.revocation_ids)
        successor = self._new_revision(successor)
        activation = self._approve(successor)
        tasks.unlink()
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        self.assertEqual(self.task.stage_id, self.stages[0])

    def test_denied_and_rolled_back_task_mutations_have_no_partial_revocation(self):
        outsider = mail_new_test_user(
            self.env, "policy_no_task_access", groups="base.group_user"
        )
        activation = self._activate()
        with self.assertRaises(AccessError):
            self.task.with_user(outsider).write({"name": "Denied"})
        with self.assertRaises(AccessError):
            self.task.with_user(outsider).unlink()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.env["project.task"].with_user(outsider).create(
                {"name": "Denied create", "project_id": self.project.id}
            )
        with self.assertRaises(_RollbackSubcase), self.env.cr.savepoint():
            self.task.with_user(self.author).write({"name": "Rolled back"})
            self.assertTrue(activation.revocation_ids)
            raise _RollbackSubcase()
        self.assertEqual(self.task.name, "Policy target")
        self.assertFalse(activation.revocation_ids)
        self.assertEqual(self.rule.activation_id, activation)
        self.assertTrue(activation._validate_current_authority())

    def _second_scope(self, company=None):
        company = company or self.env.company
        project = self.env["project.project"].create(
            {
                "name": "Second policy scope",
                "company_id": company.id,
                "agile_enabled": True,
                "agile_key": "SEC",
                "privacy_visibility": "employees",
            }
        )
        repository = self.env["project.git.repository"].create(
            {
                "name": "Second",
                "provider": "github",
                "provider_repository_id": "second",
                "canonical_url": "https://github.com/synthetic/second",
                "project_id": project.id,
            }
        )
        stages = self.env["project.task.type"].create(
            [
                {"name": name, "project_ids": [Command.link(project.id)]}
                for name in ("Source", "Target")
            ]
        )
        task = self.env["project.task"].create(
            {"name": "Second task", "project_id": project.id, "stage_id": stages[0].id}
        )
        scoped_env = self.env(
            user=self.author.id, context={"allowed_company_ids": company.ids}
        )
        rule = scoped_env["project.git.policy.rule"].create(
            {"name": "Second scope rule", "repository_id": repository.id}
        )
        revision = scoped_env["project.git.policy.revision"].create(
            {
                **self.revision_values,
                "rule_id": rule.id,
                "allowed_source_stage_ids": [Command.set(stages[0].ids)],
                "target_stage_id": stages[1].id,
            }
        )
        project.with_env(scoped_env).action_enable_git_policy()
        return project, task, rule, revision

    def test_bulk_mixed_project_edits_and_scope_move_revoke_old_and_new(self):
        project, task, rule, revision = self._second_scope()
        ordinary = self.env["project.project"].create(
            {"name": "Incoming work", "privacy_visibility": "employees"}
        )
        movable = self.env["project.task"].create(
            {"name": "Native unkeyed Task", "project_id": ordinary.id}
        )
        self.assertFalse(movable.agile_key)
        first, second = self._activate(), self._approve(revision)
        (self.task | task).with_user(self.author).write(
            {"name": "Normal mixed-scope edit"}
        )
        self.assertTrue(first.revocation_ids)
        self.assertTrue(second.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        self.assertFalse(rule.activation_id)
        first = self._approve(self._new_revision())
        second = self._approve(self._new_revision(revision))
        with self.assertRaises(ValidationError):
            self.task.with_user(self.author).write({"project_id": project.id})
        self.assertFalse(first.revocation_ids)
        self.assertFalse(second.revocation_ids)
        movable.with_user(self.author).with_context(
            git_policy_skip_revocation=True
        ).write({"project_id": project.id})
        assigned_key = movable.agile_key
        self.assertTrue(assigned_key.startswith("SEC-"))
        self.assertEqual(movable.project_id, project)
        self.assertFalse(first.revocation_ids)
        self.assertTrue(second.revocation_ids)
        self.assertEqual(self.rule.activation_id, first)
        self.assertFalse(rule.activation_id)
        with self.assertRaises(ValidationError):
            movable.with_user(self.author).write({"project_id": self.project.id})
        self.assertEqual(movable.agile_key, assigned_key)
        self.assertEqual(movable.project_id, project)
        self.assertTrue(first._validate_current_authority())
        self.assertFalse(second._validate_current_authority())

    def test_incoming_parent_scope_propagation_revokes_destination_project(self):
        project, task, rule, revision = self._second_scope()
        task_type = self.env.ref("project_agile.project_agile_item_type_task")
        subtask_type = self.env.ref("project_agile.project_agile_item_type_subtask")
        tasks = self.env["project.task"]
        ordinary = self.env["project.project"].create(
            {"name": "Incoming hierarchy", "privacy_visibility": "employees"}
        )
        parent = tasks.create(
            {
                "name": "Native parent",
                "project_id": ordinary.id,
                "agile_item_type_id": task_type.id,
            }
        )
        child = tasks.create(
            {
                "name": "Child",
                "parent_id": parent.id,
                "agile_item_type_id": subtask_type.id,
            }
        )
        self.assertEqual(child.project_id, ordinary)
        self.assertFalse(parent.agile_key)
        self.assertFalse(child.agile_key)
        first, second = self._activate(), self._approve(revision)
        parent.with_user(self.author).write({"project_id": project.id})
        self.assertTrue(parent.agile_key.startswith("SEC-"))
        self.assertTrue(child.agile_key.startswith("SEC-"))
        self.assertEqual(parent.project_id, project)
        self.assertEqual(child.project_id, project)
        self.assertEqual(child.parent_id, parent)
        self.assertEqual(parent.agile_item_type_id, task_type)
        self.assertEqual(child.agile_item_type_id, subtask_type)
        self.assertFalse(first.revocation_ids)
        self.assertTrue(second.revocation_ids)
        self.assertEqual(self.rule.activation_id, first)
        self.assertFalse(rule.activation_id)
        self.assertTrue(first._validate_current_authority())
        self.assertFalse(second._validate_current_authority())

    def test_cross_company_denial_is_atomic_and_multi_company_edit_is_terminal(self):
        company = self.env["res.company"].create({"name": "Second Task company"})
        for user in (self.author, self.approver, self.executor):
            user.company_ids = [Command.link(company.id)]
        project, task, rule, revision = self._second_scope(company)
        first, second = self._activate(), self._approve(revision)
        with self.assertRaises(AccessError):
            task.with_user(self.author).with_context(
                allowed_company_ids=self.env.company.ids
            ).write({"name": "Hidden company"})
        self.assertFalse(first.revocation_ids)
        self.assertFalse(second.revocation_ids)
        (self.task | task).with_user(self.author).with_context(
            allowed_company_ids=(self.env.company | company).ids
        ).write({"active": False})
        self.assertTrue(first.revocation_ids)
        self.assertTrue(second.revocation_ids)

    def test_native_task_assignment_and_scope_input_restore_revoke_without_validator(
        self,
    ):
        for values, restore in (
            (
                {"user_ids": [Command.link(self.executor.id)]},
                {"user_ids": [Command.clear()]},
            ),
            ({"display_in_project": False}, {"display_in_project": True}),
        ):
            with (
                self.subTest(values=values),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                activation = self._activate()
                self.task.with_user(self.author).write(values)
                self.assertTrue(activation.revocation_ids)
                self.task.with_user(self.author).write(restore)
                self.assertFalse(activation._validate_current_authority())
                raise _RollbackSubcase()

    def test_indirect_native_project_company_input_changes_revoke(self):
        partner = self.env["res.partner"].create(
            {"name": "Synthetic company source", "company_id": self.env.company.id}
        )
        self.project.partner_id = partner
        activation = self._activate()
        partner.write({"company_id": False})
        self.assertTrue(activation.revocation_ids)
        partner.write({"company_id": self.env.company.id})
        self.assertFalse(activation._validate_current_authority())
        plan = self.env["account.analytic.plan"].create(
            {"name": "Synthetic policy plan"}
        )
        account = self.env["account.analytic.account"].create(
            {
                "name": "Synthetic account",
                "plan_id": plan.id,
                "company_id": self.env.company.id,
            }
        )
        self.project.account_id = account
        activation = self._approve(self._new_revision())
        account.write({"company_id": False})
        self.assertTrue(activation.revocation_ids)
        account.write({"company_id": self.env.company.id})
        self.assertFalse(activation._validate_current_authority())

    def test_xml_identity_drift_revokes_and_current_support_is_rechecked(self):
        data = self.env["ir.model.data"].search(
            [("module", "=", "project"), ("name", "=", "task_comp_rule")]
        )
        activation = self._activate()
        data.write({"name": "temporarily_removed_task_comp_rule"})
        self.assertTrue(activation.revocation_ids)
        successor = self._new_revision()
        with self.assertRaisesRegex(AccessError, "unsupported"):
            self._approve(successor)
        data.write({"name": "task_comp_rule"})
        self.assertFalse(activation._validate_current_authority())
        self.assertTrue(self._approve(successor)._validate_current_authority())

    def test_inverse_company_membership_edit_and_restore_are_terminal(self):
        other = self.env["res.company"].create({"name": "Native inverse company scope"})
        self.executor.company_ids = [Command.link(other.id)]
        self.executor.company_id = other
        activation = self._activate()
        self.env.company.write({"user_ids": [Command.unlink(self.executor.id)]})
        self.assertNotIn(self.env.company, self.executor.company_ids)
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        self.env.company.write({"user_ids": [Command.link(self.executor.id)]})
        self.assertFalse(activation._validate_current_authority())

    def test_inverse_group_and_new_implied_group_edits_revoke(self):
        activation = self._activate()
        self.env["res.groups"].create(
            {
                "name": "New authority input",
                "implied_ids": [Command.link(self.env.ref("base.group_user").id)],
                "user_ids": [Command.link(self.executor.id)],
            }
        )
        self.assertTrue(activation.revocation_ids)
        activation = self._approve(self._new_revision())
        group = self.env.ref("project.group_project_user")
        group.write({"user_ids": [Command.unlink(self.executor.id)]})
        self.assertTrue(activation.revocation_ids)
        group.write({"user_ids": [Command.link(self.executor.id)]})
        self.assertFalse(activation._validate_current_authority())

    def _implied_group_authority(self):
        """Executor has native Project rights only through a synthetic bridge."""
        group = self.env.ref("project.group_project_user")
        bridge = self.env["res.groups"].create(
            {
                "name": "Policy native implication bridge",
                "implied_ids": [Command.link(group.id)],
            }
        )
        self.executor.write(
            {"group_ids": [Command.set((bridge | self.env.ref("base.group_user")).ids)]}
        )
        admin = mail_new_test_user(
            self.env, "policy_security_admin", groups="base.group_system"
        )
        self.assertNotEqual(admin.id, 1)
        self.assertFalse(self.env(user=admin.id).su)
        self.assertNotIn(group, self.executor.group_ids)
        self.assertIn(group, self.executor.all_group_ids)
        self.task.with_user(self.executor).check_access("write")
        return group, bridge, admin

    def test_implied_group_both_directions_denial_restore_is_terminal(self):
        group, bridge, admin = self._implied_group_authority()
        for inverse in (True, False):
            for kind in (Command.UNLINK, Command.SET, Command.CLEAR):
                with (
                    self.subTest(inverse=inverse, kind=kind),
                    self.assertRaises(_RollbackSubcase),
                    self.env.cr.savepoint(),
                ):
                    record, field, removed = (
                        (group, "implied_by_ids", bridge)
                        if inverse
                        else (bridge, "implied_ids", group)
                    )
                    original = record[field].ids
                    command = {
                        Command.UNLINK: Command.unlink(removed.id),
                        Command.SET: Command.set(
                            [i for i in original if i != removed.id]
                        ),
                        Command.CLEAR: Command.clear(),
                    }[kind]
                    activation = self._activate()
                    record.with_user(admin).with_context(
                        git_policy_skip_revocation=True
                    ).write({field: [command]})
                    self.assertNotIn(group, self.executor.all_group_ids)
                    with self.assertRaises(AccessError):
                        self.task.with_user(self.executor).check_access("write")
                    # No validator is called during the denied interval. Observe
                    # the tombstone itself before restoring native permission.
                    revoked_before_restore = bool(activation.revocation_ids)
                    pointer_cleared_before_restore = not self.rule.activation_id
                    record.with_user(admin).write({field: [Command.link(removed.id)]})
                    record.with_user(admin).write({field: [Command.set(original)]})
                    self.assertIn(group, self.executor.all_group_ids)
                    self.task.with_user(self.executor).check_access("write")
                    self.assertTrue(revoked_before_restore)
                    self.assertTrue(pointer_cleared_before_restore)
                    self.assertFalse(activation._validate_current_authority())
                    with self.assertRaises(ValidationError):
                        self._approve(self.revision)
                    successor = self._new_revision()
                    fresh = self._approve(successor)
                    self.assertNotEqual(fresh, activation)
                    self.assertEqual(fresh.revision_id, successor)
                    self.assertEqual(self.rule.activation_id, fresh)
                    self.assertGreaterEqual(fresh.activated_at, activation.activated_at)
                    self.assertTrue(fresh._validate_current_authority())
                    raise _RollbackSubcase()

    def test_implied_group_link_revokes_even_without_current_access_loss(self):
        group, bridge, admin = self._implied_group_authority()
        unused = self.env["res.groups"].create({"name": "Unused implication input"})
        for inverse in (True, False):
            with (
                self.subTest(inverse=inverse),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                record, field, linked = (
                    (group, "implied_by_ids", unused)
                    if inverse
                    else (unused, "implied_ids", group)
                )
                activation = self._activate()
                record.with_user(admin).write({field: [Command.link(linked.id)]})
                self.task.with_user(self.executor).check_access("write")
                self.assertTrue(activation.revocation_ids)
                self.assertFalse(self.rule.activation_id)
                record.with_user(admin).write({field: [Command.unlink(linked.id)]})
                self.assertFalse(activation._validate_current_authority())
                raise _RollbackSubcase()

    def test_implied_group_denied_and_enclosing_rollback_are_atomic(self):
        group, bridge, admin = self._implied_group_authority()
        for inverse in (True, False):
            with (
                self.subTest(inverse=inverse),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                record, field, removed = (
                    (group, "implied_by_ids", bridge)
                    if inverse
                    else (bridge, "implied_ids", group)
                )
                activation = self._activate()
                original = record[field]
                for command in (
                    Command.unlink(removed.id),
                    Command.set([]),
                    Command.clear(),
                    Command.link(removed.id),
                ):
                    with self.assertRaises(AccessError), self.env.cr.savepoint():
                        record.with_user(self.executor).write({field: [command]})
                    self.assertEqual(record[field], original)
                    self.assertFalse(activation.revocation_ids)
                    self.assertEqual(self.rule.activation_id, activation)
                with self.assertRaises(_RollbackSubcase), self.env.cr.savepoint():
                    record.with_user(admin).write({field: [Command.unlink(removed.id)]})
                    self.assertTrue(activation.revocation_ids)
                    self.assertFalse(self.rule.activation_id)
                    raise _RollbackSubcase()
                # Odoo's registry group graph is global, not savepoint-local.
                # Rebuild it after the deliberate test rollback (not in production).
                self.env.registry.clear_cache("groups")
                self.assertEqual(record[field], original)
                self.assertIn(group, self.executor.all_group_ids)
                self.assertFalse(activation.revocation_ids)
                self.assertEqual(self.rule.activation_id, activation)
                self.assertTrue(activation._validate_current_authority())
                raise _RollbackSubcase()

    def test_inverse_group_rule_membership_restore_is_terminal(self):
        group, bridge, admin = self._implied_group_authority()
        native = self.env.ref("project.task_comp_rule")
        self.assertFalse(native.groups)
        activation = self._activate()
        group.with_user(admin).write({"rule_groups": [Command.link(native.id)]})
        self.assertIn(group, native.groups)
        revoked_before_restore = bool(activation.revocation_ids)
        pointer_cleared_before_restore = not self.rule.activation_id
        group.with_user(admin).write({"rule_groups": [Command.unlink(native.id)]})
        self.assertFalse(native.groups)
        self.assertTrue(revoked_before_restore)
        self.assertTrue(pointer_cleared_before_restore)
        self.assertFalse(activation._validate_current_authority())
        self.assertTrue(
            self._approve(self._new_revision())._validate_current_authority()
        )

    def test_actor_partner_reassignment_restore_cannot_reuse_epoch(self):
        original = self.executor.partner_id
        partner = self.env["res.partner"].create(
            {"name": "New native identity partner"}
        )
        activation = self._activate()
        self.executor.write({"partner_id": partner.id})
        self.assertTrue(activation.revocation_ids)
        self.executor.write({"partner_id": original.id})
        self.assertFalse(activation._validate_current_authority())

    def test_company_archival_restore_revokes_and_refuses_new_approval(self):
        company = self.env["res.company"].create({"name": "Archived policy company"})
        for user in (self.author, self.approver, self.executor):
            user.company_ids = [Command.link(company.id)]
        project, task, rule, revision = self._second_scope(company)
        activation = self._approve(revision)
        company.write({"active": False})
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(rule.activation_id)
        with self.assertRaises(AccessError):
            self._approve(revision)
        company.write({"active": True})
        self.assertFalse(activation._validate_current_authority())

    def test_shared_stage_inverse_edit_revokes_other_project_epoch(self):
        project, task, rule, revision = self._second_scope()
        stage = self.stages[2]
        project.with_user(self.author).write({"type_ids": [Command.link(stage.id)]})
        activation = self._activate()
        project.with_user(self.author).write({"type_ids": [Command.unlink(stage.id)]})
        project.with_user(self.author).write({"type_ids": [Command.link(stage.id)]})
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(self.rule.activation_id)
        self.assertFalse(activation._validate_current_authority())

    def test_current_profile_field_drift_revokes_before_restoration(self):
        activation = self._activate()
        with patch.object(
            self.env["project.task"]._fields["name"], "company_dependent", True
        ):
            self.assertFalse(activation._validate_current_authority())
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(activation._validate_current_authority())

    def test_company_scope_and_serial_revision_are_server_derived(self):
        self.assertEqual(self.rule.owner_id, self.author)
        self.assertEqual(self.revision.company_id, self.project.company_id)
        second = (
            self.env["project.git.policy.revision"]
            .with_user(self.author)
            .create(self.revision_values)
        )
        self.assertEqual((self.revision.revision, second.revision), (1, 2))
        for key in (
            "company_id",
            "project_id",
            "owner_id",
            "revision",
            "approver_id",
            "approved_at",
        ):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                self.env["project.git.policy.revision"].with_user(self.author).create(
                    {**self.revision_values, key: 1}
                )

    def test_stage_and_check_bounds_are_enforced_on_create_and_write(self):
        other_project = self.env["project.project"].create(
            {"name": "Other", "company_id": self.env.company.id}
        )
        foreign = self.env["project.task.type"].create(
            {"name": "Foreign", "project_ids": [Command.link(other_project.id)]}
        )
        invalid = (
            {"allowed_source_stage_ids": [Command.clear()]},
            {"target_stage_id": self.stages[0].id},
            {"target_stage_id": foreign.id},
            {"allowed_source_stage_ids": [Command.set(foreign.ids)]},
            {"target_branch": "*"},
            {"target_branch": " "},
            {"target_branch": "x" * 256},
            {"trigger": "push"},
            {"effect": "complete_task"},
            {"expression": "True"},
            {"model": "project.task"},
            {"method": "write"},
            {"field": "state"},
            {"domain": []},
            {"mode": "apply"},
            {"required_check_ids": [Command.create({"name": "*"})]},
            {
                "required_check_ids": [
                    Command.create({"name": "CI"}),
                    Command.create({"name": "CI"}),
                ]
            },
            {
                "required_check_ids": [
                    Command.create({"name": str(i)}) for i in range(21)
                ]
            },
        )
        # Local invalid-value mapping; unittest.mock.patch is not used here.
        for patch in invalid:  # noqa: F402
            expected = (
                ValueError
                if {"trigger", "effect"}.intersection(patch)
                else ValidationError
            )
            with (
                self.subTest(patch=patch),
                self.env.cr.savepoint(),
                self.assertRaises(expected),
            ):
                self.env["project.git.policy.revision"].with_user(self.author).create(
                    {**self.revision_values, **patch}
                )
            with (
                self.subTest(write=patch),
                self.env.cr.savepoint(),
                self.assertRaises(expected),
            ):
                self.revision.write(patch)
        stages = self.env["project.task.type"].create(
            [
                {"name": str(i), "project_ids": [Command.link(self.project.id)]}
                for i in range(21)
            ]
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.revision.write({"allowed_source_stage_ids": [Command.set(stages.ids)]})
        self.revision.write(
            {"required_check_ids": [Command.create({"name": "CI / Linux"})]}
        )
        self.assertEqual(self.revision.required_check_ids.name, "CI / Linux")
        check = self.revision.required_check_ids
        with self.assertRaises(ValidationError):
            check.write({"revision_id": 999999})

    # Replace context to exercise the exact forged-default payload in isolation.
    def test_default_context_cannot_mint_controls_or_identity(self):
        # pylint: disable=context-overridden
        context = {
            "default_company_id": 1,
            "default_owner_id": 1,
            "default_approver_id": 1,
            "default_approved_at": "2020-01-01",
            "default_activation_id": 1,
            "default_git_policy_enabled": True,
            "default_git_policy_mode": "apply",
            "default_git_policy_last_activation_id": 1,
            "default_git_policy_last_effect_id": 1,
            "default_git_policy_evidence_version": 99,
            "default_last_effect_id": 1,
            "policy_trusted": True,
            "policy_execution_user_id": 1,
        }
        rule = (
            self.env["project.git.policy.rule"]
            .with_user(self.author)
            .with_context(context)
            .create(
                {
                    "name": "Safe",
                    "repository_id": self.repository.id,
                }
            )
        )
        revision = (
            self.env["project.git.policy.revision"]
            .with_user(self.author)
            .with_context(context)
            .create(
                {
                    **self.revision_values,
                    "rule_id": rule.id,
                }
            )
        )
        self.assertEqual(rule.owner_id, self.author)
        self.assertFalse(rule.activation_id)
        self.assertFalse(revision.approver_id)
        self.assertEqual(revision.execution_user_id, self.executor)
        project = (
            self.env["project.project"]
            .with_context(context)
            .create({"name": "Defaults"})
        )
        self.assertFalse(project.git_policy_enabled)
        self.assertEqual(project.git_policy_mode, "dry_run")
        self.assertFalse(project.git_policy_last_activation_id)
        self.assertFalse(rule.sudo().last_effect_id)
        values = self.repository.read(
            [
                "name",
                "provider",
                "provider_repository_id",
                "canonical_url",
                "project_id",
            ]
        )[0]
        values.pop("id")
        values["provider_repository_id"] += "-defaults"
        values["project_id"] = values["project_id"][0]
        repository = self.repository.with_context(context).create(values)
        self.assertEqual(repository.git_policy_evidence_version, 0)
        self.assertFalse(repository.git_policy_last_activation_id)
        self.assertFalse(repository.git_policy_last_effect_id)
        with self.assertRaises(ValidationError):
            self.repository.create({**values, "git_policy_evidence_version": 99})

    def test_policy_relations_cannot_edit_native_stages(self):
        for command in (
            Command.update(self.stages[0].id, {"name": "Unauthorized nested edit"}),
            Command.create(
                {"name": "Nested stage", "project_ids": [Command.link(self.project.id)]}
            ),
            Command.delete(self.stages[1].id),
        ):
            with (
                self.subTest(command=command),
                self.env.cr.savepoint(),
                self.assertRaises(ValidationError),
            ):
                self.revision.write({"allowed_source_stage_ids": [command]})
        self.assertEqual(self.stages[0].name, "Develop")
        self.assertEqual(self.task.stage_id, self.stages[0])

    def test_plain_manager_and_project_user_cannot_configure_or_activate(self):
        for user in (self.manager, self.executor):
            with self.subTest(user=user.login):
                with self.assertRaises(AccessError):
                    self.env["project.git.policy.rule"].with_user(user).create(
                        {"name": "Denied", "repository_id": self.repository.id}
                    )
                for method in ("action_enable_git_policy", "action_disable_git_policy"):
                    with self.assertRaises(AccessError):
                        getattr(self.project.with_user(user), method)()
                with self.assertRaises(AccessError):
                    self.revision.with_user(user).action_activate(
                        acknowledge_native_side_effects=True
                    )
                with self.assertRaises(AccessError):
                    self.rule.with_user(user).action_disable()
                with self.assertRaises(AccessError):
                    self.rule.with_user(user).action_transfer_owner(self.approver.id)
                with self.assertRaises(AccessError):
                    self.revision.with_user(user).action_new_revision()
                with self.assertRaises(AccessError):
                    self.revision.with_user(user).write({"target_branch": "release"})

    def test_raw_control_activation_and_history_writes_are_denied(self):
        for values in (
            {"git_policy_enabled": True},
            {"git_policy_mode": "apply"},
            {"git_policy_authority_epoch": 2},
            {"git_policy_last_activation_id": 1},
        ):
            with self.assertRaises(ValidationError):
                self.project.with_user(self.author).write(values)
        for values in (
            {"owner_id": self.approver.id},
            {"activation_id": 1},
            {"last_effect_id": 1},
            {"repository_id": self.repository.id},
        ):
            with self.assertRaises(ValidationError):
                self.rule.write(values)
        for field in (
            "git_policy_evidence_version",
            "git_policy_last_activation_id",
            "git_policy_last_effect_id",
        ):
            with self.assertRaises(ValidationError):
                self.repository.with_context(policy_trusted=True).write({field: 1})
        for model in ("project.git.policy.activation", "project.git.policy.revocation"):
            with self.assertRaises(AccessError):
                self.env[model].with_user(self.approver).with_context(
                    policy_trusted=True
                ).create({})
        with self.assertRaises(ValidationError):
            self.project.with_user(self.author).action_enable_git_policy(mode="eval")

    def test_two_person_approval_acknowledgment_and_actual_task_authority(self):
        with self.assertRaises(ValidationError):
            self.revision.with_user(self.approver).action_activate(
                acknowledge_native_side_effects=True
            )
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

    def test_executor_uid_one_portal_inactive_and_foreign_company_denied(self):
        portal = mail_new_test_user(
            self.env, "policy_portal", groups="base.group_portal"
        )
        inactive = mail_new_test_user(
            self.env, "policy_inactive", groups="project.group_project_user"
        )
        inactive.active = False
        self.project.with_user(self.author).action_enable_git_policy()
        for identity in (self.env.ref("base.user_root"), portal, inactive):
            with (
                self.subTest(identity=identity.id),
                self.env.cr.savepoint(),
                self.assertRaises(AccessError),
            ):
                self.revision.write({"execution_user_id": identity.id})
                self.revision.with_user(self.approver).action_activate(
                    acknowledge_native_side_effects=True
                )

    def test_custom_task_rule_denial_is_not_model_acl_authority(self):
        self.env["ir.rule"].create(
            {
                "name": "Deny exact policy Task",
                "model_id": self.env["ir.model"]._get("project.task").id,
                "domain_force": "[('name', '!=', 'Policy target')]",
            }
        )
        self.env["project.task"].with_user(self.executor).browse().check_access("write")
        with self.assertRaises(AccessError):
            self.task.with_user(self.executor).check_access("write")
        self.project.with_user(self.author).action_enable_git_policy()
        with self.assertRaises(AccessError):
            self.revision.with_user(self.approver).action_activate(
                acknowledge_native_side_effects=True
            )
        self.assertFalse(self.rule.activation_id)

    def test_custom_project_denial_and_forged_record_ids(self):
        self.env["ir.rule"].create(
            {
                "name": "Deny policy Project",
                "model_id": self.env["ir.model"]._get("project.project").id,
                "domain_force": "[('name', '!=', 'Finite policy')]",
            }
        )
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
            self.revision.with_user(self.approver).action_activate(
                acknowledge_native_side_effects=True
            )

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
            (
                "group_ids",
                [Command.clear(), Command.link(self.env.ref("base.group_user").id)],
            ),
        ):
            with (
                self.subTest(field=field),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                first = self._activate()
                self.executor.write({field: value})
                self._assert_revoked(first)
                self.executor.active = True
                self.executor.group_ids = [
                    Command.link(self.env.ref("project.group_project_user").id)
                ]
                self.assertFalse(first._validate_current_authority())
                # Roll back this subcase without rolling back the testcase fixture.
                raise _RollbackSubcase()

    def test_security_rule_revocation_stage_changes_and_repository_archive(self):
        activation = self._activate()
        self.env["ir.rule"].create(
            {
                "name": "Authority changed",
                "model_id": self.env["ir.model"]._get("project.task").id,
                "domain_force": "[('active', 'in', [True, False])]",
            }
        )
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
        # Native FK/ORM deletion rejection varies by installed extensions;
        # preserve the existing no-delete assertion and following state readback.
        with self.env.cr.savepoint(), self.assertRaises(Exception):  # noqa: B017
            self.repository.unlink()
        self.assertTrue(activation.exists())

    # Exact replacement tests the supplied multi-company scope, not inherited keys.
    def test_multiple_enabled_companies_and_reassignment_invalidate_history(self):
        # pylint: disable=context-overridden
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

    # Preserve the existing native test identifier.
    def test_company_context_cannot_grant_scope_and_companyless_projects_stay_facts_only(  # noqa: E501
        self,
    ):
        company = self.env["res.company"].create({"name": "Forbidden company"})
        with self.assertRaises(AccessError):
            self.rule.with_context(allowed_company_ids=[company.id]).write(
                {"name": "Forged"}
            )
        self.project.company_id = False
        with self.assertRaises(AccessError):
            self.project.with_user(self.author).action_enable_git_policy()

    def test_public_form_and_wizard_require_fresh_approver_acknowledgment(self):
        self.project.with_user(self.author).action_enable_git_policy()
        for user in (self.executor, self.manager):
            with self.assertRaises(AccessError):
                self.revision.with_user(user).action_activate_from_form()
            with self.assertRaises(AccessError):
                self.env["project.git.policy.approval.wizard"].with_user(user).create(
                    {"revision_id": self.revision.id}
                )
        action = (
            self.revision.with_user(self.approver)
            .with_context(
                default_acknowledge_native_side_effects=True,
                default_execution_user_id=1,
            )
            .action_activate_from_form()
        )
        wizard = (
            self.env[action["res_model"]]
            .with_user(self.approver)
            .browse(action["res_id"])
        )
        self.assertFalse(wizard.acknowledge_native_side_effects)
        with self.assertRaises(ValidationError):
            wizard.action_approve()
        with self.assertRaises(ValidationError):
            wizard.write({"revision_id": self.revision.id})
        wizard.write({"acknowledge_native_side_effects": True})
        self.assertEqual(
            wizard.action_approve(), {"type": "ir.actions.act_window_close"}
        )
        self.assertEqual(self.rule.activation_id.execution_user_id, self.executor)
        self.assertEqual(self.task.stage_id, self.stages[0])

    # The adversarial test must replace context with its exact forged payload.
    def test_activation_never_trusts_context_for_mode_identity_or_acknowledgment(self):
        # pylint: disable=context-overridden
        self.project.with_user(self.author).action_enable_git_policy()
        context = {
            "policy_execution_user_id": 1,
            "default_execution_user_id": 1,
            "git_policy_mode": "apply",
            "acknowledge_native_side_effects": True,
            "policy_trusted": True,
            "force_company": 1,
        }
        revision = self.revision.with_user(self.approver).with_context(context)
        with self.assertRaises(ValidationError):
            revision.action_activate()
        result = revision.action_activate(acknowledge_native_side_effects=True)
        activation = self.env["project.git.policy.activation"].browse(
            result["activation_id"]
        )
        self.assertEqual(activation.execution_user_id, self.executor)
        self.assertEqual(activation.mode, "dry_run")
        self.assertEqual(activation.approver_id, self.approver)

    def test_emergency_system_administrator_can_disable_but_not_activate(self):
        system = mail_new_test_user(
            self.env,
            "policy_system",
            groups="base.group_system,project.group_project_manager",
        )
        activation = self._activate()
        self.assertFalse(
            system.has_group("project_agile_git_automation.group_git_policy_manager")
        )
        self.rule.with_user(system).action_disable()
        self._assert_revoked(activation)
        self.project.with_user(system).action_disable_git_policy()
        with self.assertRaises(AccessError):
            self.project.with_user(system).action_enable_git_policy()
        with self.assertRaises(AccessError):
            self.revision.with_user(system).action_activate(
                acknowledge_native_side_effects=True
            )

    def test_private_project_and_custom_visibility_apply_to_every_policy_read_surface(
        self,
    ):
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
        deny = self.env["ir.rule"].create(
            {
                "name": "Hide Project from policy reads",
                "model_id": self.env["ir.model"]._get("project.project").id,
                "domain_force": "[('name', '!=', 'Finite policy')]",
            }
        )
        self.assertFalse(
            self.rule.with_user(self.executor).search([("id", "=", self.rule.id)])
        )
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
        other_company = self.env["res.company"].create(
            {"name": "Executor alternate company"}
        )
        self.executor.company_ids = [Command.link(other_company.id)]
        activation = self._activate()
        self.executor.write(
            {
                "company_id": other_company.id,
                "company_ids": [Command.set(other_company.ids)],
            }
        )
        self._assert_revoked(activation)
        self.executor.company_ids = [Command.link(self.env.company.id)]
        self.assertFalse(activation._validate_current_authority())

    def test_removed_capability_and_acl_changes_do_not_restore_approval(self):
        activation = self._activate()
        self.author.group_ids = [
            Command.unlink(
                self.env.ref("project_agile_git_automation.group_git_policy_manager").id
            )
        ]
        self._assert_revoked(activation)
        self.author.group_ids = [
            Command.link(
                self.env.ref("project_agile_git_automation.group_git_policy_manager").id
            )
        ]
        self.assertFalse(activation._validate_current_authority())
        revision = self._new_revision()
        activation = self._approve(revision)
        acl = self.env["ir.model.access"].create(
            {
                "name": "Synthetic Task authority",
                "model_id": self.env["ir.model"]._get("project.task").id,
                "group_id": self.env.ref("project.group_project_user").id,
                "perm_read": True,
            }
        )
        self._assert_revoked(activation)
        revision = self._new_revision(revision)
        activation = self._approve(revision)
        acl.write({"perm_write": True})
        self._assert_revoked(activation)
        revision = self._new_revision(revision)
        activation = self._approve(revision)
        acl.unlink()
        self._assert_revoked(activation)

    # Preserve the existing native test identifier.
    def test_unlinked_source_stages_and_stage_notifications_revoke_even_after_restoration(  # noqa: E501
        self,
    ):
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
        rule = (
            self.env["project.git.policy.rule"]
            .with_user(self.author)
            .create(
                {
                    "name": "Second explicit rule",
                    "repository_id": self.repository.id,
                }
            )
        )
        revision = (
            self.env["project.git.policy.revision"]
            .with_user(self.author)
            .create(
                {
                    **self.revision_values,
                    "rule_id": rule.id,
                }
            )
        )
        second = self._approve(revision)
        self.assertTrue(first._validate_current_authority())
        self.assertTrue(second._validate_current_authority())
        self.project.with_user(self.author).action_disable_git_policy()
        self.assertFalse(first._validate_current_authority())
        self.assertFalse(second._validate_current_authority())

    def test_project_and_task_unfollow_restore_cannot_resurrect_approval(self):
        for record in (self.project, self.task):
            with (
                self.subTest(model=record._name),
                self.assertRaises(_RollbackSubcase),
                self.env.cr.savepoint(),
            ):
                self.project.privacy_visibility = "followers"
                self.project.message_subscribe(partner_ids=self.executor.partner_id.ids)
                self.task.message_subscribe(partner_ids=self.executor.partner_id.ids)
                activation = self._activate()
                record.with_user(self.author).message_unsubscribe(
                    partner_ids=self.executor.partner_id.ids
                )
                # Restore before validation: revocation must be a durable native
                # mutation hook, not dependent on catching a temporary denial.
                record.message_subscribe(partner_ids=self.executor.partner_id.ids)
                self.assertTrue(activation.revocation_ids)
                self.assertFalse(activation._validate_current_authority())
                raise _RollbackSubcase()

    def test_follower_reassignment_revokes_original_project_authority(self):
        self.project.message_subscribe(partner_ids=self.executor.partner_id.ids)
        activation = self._activate()
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", "project.project"),
                ("res_id", "=", self.project.id),
                ("partner_id", "=", self.executor.partner_id.id),
            ]
        )
        partner = self.env["res.partner"].create(
            {"name": "Synthetic replacement follower"}
        )
        follower.write({"partner_id": partner.id})
        follower.write({"partner_id": self.executor.partner_id.id})
        self.assertTrue(activation.revocation_ids)
        self.assertFalse(activation._validate_current_authority())

    def test_all_policy_read_surfaces_and_public_controls_reject_hidden_project(self):
        self.executor.group_ids = [
            Command.link(self.env.ref("base.group_allow_export").id)
        ]
        self.revision.write({"required_check_ids": [Command.create({"name": "CI"})]})
        activation = self._activate()
        self.project.privacy_visibility = "followers"
        records = (
            self.rule,
            self.revision,
            self.revision.required_check_ids,
            activation,
            activation.revocation_ids,
        )
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

        self.env["ir.rule"].create(
            {
                "name": "Hide configured Project even from capability holders",
                "model_id": self.env["ir.model"]._get("project.project").id,
                "domain_force": f"[('id', '!=', {self.project.id:d})]",
            }
        )
        calls = (
            (self.rule, "action_disable", {}),
            (self.rule, "action_transfer_owner", {"new_owner_id": self.approver.id}),
            (self.rule, "unlink", {}),
            (self.revision, "action_new_revision", {}),
            (self.revision, "action_activate_from_form", {}),
            (
                self.revision.with_user(self.approver),
                "action_activate",
                {"acknowledge_native_side_effects": True},
            ),
            (self.project.with_user(self.author), "action_enable_git_policy", {}),
            (self.project.with_user(self.author), "action_disable_git_policy", {}),
        )
        for record, method, kwargs in calls:
            with self.subTest(method=method), self.assertRaises(AccessError):
                getattr(record, method)(**kwargs)
        with self.assertRaises(AccessError):
            self.env["project.git.policy.approval.wizard"].with_user(
                self.approver
            ).create({"revision_id": self.revision.id})

    def test_required_checks_and_revision_batch_create_cannot_mutate_approved_history(
        self,
    ):
        self.revision.write({"required_check_ids": [Command.create({"name": "CI"})]})
        activation = self._activate()
        check = self.revision.required_check_ids
        for method, values in (("write", {"name": "Other CI"}), ("unlink", None)):
            with self.assertRaises(ValidationError):
                getattr(check, method)(values) if values is not None else check.unlink()
        with self.assertRaises(ValidationError):
            self.env["project.git.policy.required.check"].with_user(self.author).create(
                {"revision_id": self.revision.id, "name": "Extra"}
            )
        self.assertTrue(activation._validate_current_authority())
        revisions = (
            self.env["project.git.policy.revision"]
            .with_user(self.author)
            .create(
                [
                    self.revision_values,
                    self.revision_values,
                ]
            )
        )
        self.assertEqual(revisions.mapped("revision"), [2, 3])
        self._assert_revoked(activation)


class _RollbackSubcase(Exception):
    """Internal testcase savepoint rollback marker."""

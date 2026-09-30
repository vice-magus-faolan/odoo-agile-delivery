"""Imported Odoo 19 fixture tests; no automation executor exists in this slice."""

from odoo.fields import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGitPolicyContract(TransactionCase):
    def setUp(self):
        super().setUp()
        self.reader = mail_new_test_user(
            self.env, "policy_reader", groups="project.group_project_user,base.group_allow_export",
        )
        self.manager = mail_new_test_user(
            self.env, "policy_manager", groups="project.group_project_manager",
        )
        self.project = self.env["project.project"].create({
            "name": "Policy fixture", "company_id": self.env.company.id,
            "privacy_visibility": "employees", "agile_enabled": True, "agile_key": "POL",
        })
        self.repository = self._repository(self.project, "policy")
        self.delivery = self._delivery(self.repository, "policy-fixture")
        self.values = {"repository_id": self.repository.id, "delivery_id": self.delivery.id}
        self.audit = self.env["project.git.policy.audit"].sudo().create(self.values)

    def _repository(self, project, suffix):
        return self.env["project.git.repository"].sudo().create({
            "name": suffix, "provider": "github", "provider_repository_id": suffix,
            "canonical_url": "https://github.com/synthetic/" + suffix,
            "project_id": project.id,
        })

    def _delivery(self, repository, suffix):
        return self.env["project.git.delivery"].sudo().create({
            "repository_id": repository.id, "provider_delivery_id": suffix,
            "event_type": "pull_request", "payload_sha256": "a" * 64, "payload_size": 2,
        })

    def test_defaults_are_inert_dry_run_without_configuration_or_cron(self):
        self.assertEqual(self.audit.mode, "dry_run")
        self.assertEqual(self.audit.reason, "contract_fixture")
        self.assertNotIn("project.git.policy.rule", self.env.registry)
        model = self.env["ir.model"]._get("project.git.policy.audit")
        self.assertFalse(self.env["ir.cron"].search([("model_id", "=", model.id)]))
        self.assertFalse(hasattr(self.audit, "action_apply"))

    def test_fixture_creation_rejects_user_manager_and_forged_context(self):
        for user in (self.reader, self.manager):
            with self.subTest(user=user.login), self.assertRaises(AccessError):
                self.env["project.git.policy.audit"].with_user(user).with_context(
                    policy_trusted=True, policy_execution_user_id=1,
                    git_delivery_lease="forged", allowed_company_ids=[self.env.company.id],
                ).create(self.values)
        for model_name, values in (
            ("project.git.delivery", {
                "repository_id": self.repository.id, "provider_delivery_id": "forged",
                "event_type": "pull_request", "payload_sha256": "b" * 64, "payload_size": 2,
            }),
            ("project.git.pull.request", {
                "repository_id": self.repository.id, "provider_request_id": "forged",
                "state": "merged", "provenance_delivery_id": self.delivery.id,
            }),
        ):
            with self.assertRaises(AccessError):
                self.env[model_name].with_user(self.manager).create(values)

    def test_audit_remains_append_only_for_every_identity(self):
        for record in (self.audit, self.audit.with_user(self.reader), self.audit.with_user(self.manager)):
            with self.assertRaises(ValidationError):
                record.write({"reason": "contract_fixture"})
            with self.assertRaises(ValidationError):
                record.unlink()
        self.assertTrue(self.audit.exists())

    def test_cross_repository_provenance_and_unbounded_reasons_are_rejected(self):
        other = self._repository(self.project, "policy-other")
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.env["project.git.policy.audit"].sudo().create({
                "repository_id": other.id, "delivery_id": self.delivery.id,
            })
        with self.assertRaises(ValueError):
            self.env["project.git.policy.audit"].sudo().create({
                **self.values, "reason": "untrusted provider text",
            })

    def test_private_project_visibility_applies_to_read_search_count_group_export(self):
        self.project.privacy_visibility = "followers"
        visible = self.env["project.git.policy.audit"].with_user(self.reader)
        visible.browse().check_access("read")
        self.assertFalse(visible.search([("id", "=", self.audit.id)]))
        self.assertEqual(visible.search_count([("id", "=", self.audit.id)]), 0)
        self.assertFalse(visible._read_group([("id", "=", self.audit.id)], [], ["__count"])[0][0])
        with self.assertRaises(AccessError):
            visible.browse(self.audit.id).read(["reason"])
        with self.assertRaises(AccessError):
            visible.browse(self.audit.id).export_data(["reason"])
        self.project.message_subscribe(partner_ids=self.reader.partner_id.ids)
        self.assertEqual(visible.search([("id", "=", self.audit.id)]).ids, self.audit.ids)

    def test_company_scope_for_nonadmin_manager_and_multiple_enabled_companies(self):
        company = self.env["res.company"].create({"name": "Policy fixture second company"})
        project = self.env["project.project"].with_company(company).create({
            "name": "Other policy fixture", "company_id": company.id,
            "privacy_visibility": "employees", "agile_enabled": True, "agile_key": "POX",
        })
        repository = self._repository(project, "policy-company")
        delivery = self._delivery(repository, "policy-company")
        audit = self.env["project.git.policy.audit"].sudo().create({
            "repository_id": repository.id, "delivery_id": delivery.id,
        })
        self.manager.company_ids = [Command.link(company.id)]
        model = self.env["project.git.policy.audit"].with_user(self.manager).with_context(
            allowed_company_ids=[self.env.company.id],
        )
        model.browse().check_access("read")
        self.assertFalse(model.search([("id", "=", audit.id)]))
        with self.assertRaises(AccessError):
            model.browse(audit.id).read(["reason"])
        enabled = model.with_context(allowed_company_ids=[self.env.company.id, company.id])
        self.assertEqual(set(enabled.search([("id", "in", (self.audit | audit).ids)]).ids), set((self.audit | audit).ids))
        with self.assertRaises(AccessError):
            model.with_user(self.reader).with_context(allowed_company_ids=[company.id]).search([])

    def test_native_stage_transition_is_not_completion_and_keeps_scrum_scope(self):
        stages = self.env["project.task.type"].create([
            {"name": name, "project_ids": [Command.link(self.project.id)]}
            for name in ("Development", "Ready for QA")
        ])
        task = self.env["project.task"].create({
            "name": "Native semantics fixture", "project_id": self.project.id,
            "stage_id": stages[0].id,
        })
        task.state = "03_approved"
        before = task.read(["agile_key", "agile_story_points", "parent_id"])[0]
        scope_count = 0
        if "sprint_id" in task._fields:
            scope_count = self.env["project.sprint.scope.event"].search_count([("task_id", "=", task.id)])
        task.with_user(self.reader).write({"stage_id": stages[1].id})
        self.assertEqual(task.state, "01_in_progress")
        self.assertFalse(task.is_closed)
        self.assertTrue(task.date_last_stage_update)
        self.assertEqual(before, task.read(["agile_key", "agile_story_points", "parent_id"])[0])
        if "sprint_id" in task._fields:
            self.assertFalse(task.sprint_id)
            self.assertEqual(self.env["project.sprint.scope.event"].search_count([("task_id", "=", task.id)]), scope_count)
        task.state = "1_done"
        task.with_user(self.reader).write({"stage_id": stages[0].id})
        self.assertEqual(task.state, "1_done")

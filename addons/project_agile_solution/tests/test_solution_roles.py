from unittest import TestCase as PythonTestCase

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import Form, TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestSolutionRoles(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Role foreign"})
        cls.analyst = mail_new_test_user(
            cls.env,
            "solution_role_analyst",
            groups="project_agile_solution.group_business_analyst,base.group_allow_export",
            company_id=cls.company.id,
            company_ids=[Command.set(cls.company.ids)],
        )
        cls.member = mail_new_test_user(
            cls.env, "solution_role_member", groups="project_agile.group_agile_member"
        )
        cls.approver = mail_new_test_user(
            cls.env,
            "solution_role_approver",
            groups="project.group_project_manager",
            company_id=cls.company.id,
            company_ids=[Command.set((cls.company | cls.other_company).ids)],
        )
        cls.peer = mail_new_test_user(
            cls.env,
            "solution_role_peer",
            groups="project_agile_solution.group_business_analyst",
        )
        cls.administrator = mail_new_test_user(
            cls.env,
            "solution_role_administrator",
            groups="project.group_project_manager",
        )
        cls.project = cls._project("ROLEBA", cls.company)
        cls.hidden = cls._project("ROLEHIDE", cls.company, "followers")
        cls.foreign = cls._project("ROLEOTHER", cls.other_company)
        cls.solution = cls.env["project.agile.solution"].create(
            {
                "name": "Role lineage",
                "project_id": cls.project.id,
            }
        )

    @classmethod
    def _project(cls, key, company, privacy="employees"):
        return cls.env["project.project"].create(
            {
                "name": key,
                "agile_enabled": True,
                "agile_key": key,
                "privacy_visibility": privacy,
                "company_id": company.id,
            }
        )

    def _requirement(self, solution=None, user=None):
        model = self.env["project.agile.requirement"].with_user(user or self.analyst)
        identity = model.create(
            {
                "name": "Role requirement",
                "solution_id": (solution or self.solution).id,
            }
        )
        return (
            self.env["project.agile.requirement.revision"]
            .with_env(model.env)
            .create(
                {
                    "requirement_id": identity.id,
                    "title": "Restricted authoring",
                    "requirement_type": "fr",
                    "description": "Author intent without approval",
                    "rationale": "Least privilege",
                    "priority": "must",
                    "verification_method": "Actual role workflows",
                    "acceptance_expectations": "Author succeeds; approval is refused",
                }
            )
        )

    def _revision(self, requirement):
        documents = self.env["project.agile.solution.document"].with_user(self.analyst)
        with Form(documents) as form:
            form.name = "Role document"
            form.solution_id = self.solution
            form.approver_id = self.approver
        document = form.record
        action = document.action_new_revision()
        revision = (
            self.env[action["res_model"]]
            .with_user(self.analyst)
            .browse(action["res_id"])
        )
        revision.write({"requirement_revision_ids": [Command.set(requirement.ids)]})
        action = revision.action_request_template()
        self.env[action["res_model"]].with_user(self.analyst).with_context(
            **action["context"]
        ).create(
            {
                "template_id": self.env.ref(
                    "project_agile_solution.template_internal_brief"
                ).id
            }
        ).action_confirm()
        revision.section_ids[0].write({"body": "Authored without administration"})
        return revision

    def _preview(self, requirement, **values):
        model = self.env["project.agile.solution.task.intent"].with_user(self.analyst)
        return model.create(
            {
                "name": "Author preview",
                "operation": "create",
                "solution_id": self.solution.id,
                "agile_item_type_id": self.env.ref(
                    "project_agile.project_agile_item_type_story"
                ).id,
                "requirement_revision_ids": [Command.set(requirement.ids)],
                **values,
            }
        )

    def test_author_documents_preview_links_and_successors_not_approval(self):
        self.assertFalse(self.analyst.has_group("project.group_project_manager"))
        self.assertTrue(self.analyst.has_group("project_agile.group_agile_member"))
        self.env["project.agile.solution"].with_user(self.analyst).create(
            {
                "name": "BA lineage",
                "project_id": self.project.id,
            }
        )
        requirement = self._requirement()
        requirement.write({"rationale": "Author can refine intent"})
        revision = self._revision(requirement)
        revision.action_submit()
        with self.assertRaises(AccessError):
            revision.action_approve()
        self.assertEqual(revision.state, "review")
        with self.assertRaises(AccessError):
            revision.action_request_return()
        action = revision.with_user(self.approver).action_request_return()
        self.env[action["res_model"]].with_user(self.approver).with_context(
            **action["context"]
        ).create({"reason": "Reviewer requests clearer intent"}).action_confirm()
        revision.section_ids[0].write({"body": "Author corrects returned draft"})
        revision.action_submit()
        revision.with_user(self.approver).action_approve()
        self.assertEqual(revision.state, "approved")
        self.assertEqual(revision.approved_by_id, self.approver)
        snapshot = revision.action_read_snapshot()["snapshot_json"]
        successor = revision.browse(revision.action_new_revision()["res_id"])
        self.assertEqual(successor.state, "draft")
        self.assertEqual(revision.action_read_snapshot()["snapshot_json"], snapshot)
        requirement2 = requirement.browse(
            requirement.requirement_id.action_new_revision()["res_id"]
        )
        requirement2.write({"description": "Explicit successor"})
        intent = self._preview(requirement2)
        action = intent.action_request_confirmation()
        result = (
            self.env[action["res_model"]]
            .with_user(self.analyst)
            .with_context(**action["context"])
            .create({})
            .action_confirm()
        )
        self.assertEqual(intent.action_confirm()["res_id"], result["res_id"])
        task = intent.task_id
        link = (
            self.env["project.agile.requirement.task.link"]
            .with_user(self.analyst)
            .search([("task_id", "=", task.id)])
        )
        self.assertEqual(link.requirement_revision_id, requirement2)
        # Also exercise direct ORM linking, not only the preview route.
        other = self._requirement()
        self.env["project.agile.requirement.task.link"].with_user(self.analyst).create(
            {
                "task_id": task.id,
                "requirement_revision_id": other.id,
            }
        )
        with self.assertRaises(ValidationError):
            revision.document_id.write({"approver_id": self.analyst.id})

    def test_return_denies_peer_and_author_without_mutating_review(self):
        revision = self._revision(self._requirement())
        revision.action_submit()
        fields = [
            "state",
            "return_reason",
            "snapshot_json",
            "snapshot_sha256",
            "submitted_by_id",
            "submitted_at",
            "approved_by_id",
            "approved_at",
            "write_date",
            "section_ids",
            "requirement_revision_ids",
        ]
        before = revision.read(fields)
        for user in (self.peer, self.analyst):
            caller = revision.with_user(user)
            wizard = (
                self.env["project.agile.solution.revision.wizard"]
                .with_user(user)
                .create(
                    {
                        "revision_id": revision.id,
                        "operation": "return",
                        "reason": "Not a reviewer decision",
                    }
                )
            )
            for action in (
                caller.action_request_return,
                lambda caller=caller: caller.action_return_to_draft("Peer return"),
                lambda caller=caller: caller.sudo()
                .with_context(sudo=True, solution_trusted=True)
                .action_return_to_draft("Forged review authority"),
                wizard.action_confirm,
            ):
                with self.subTest(user=user.login, action=action):
                    # No rollback savepoint: a caught denial must leave review intact.
                    with PythonTestCase.assertRaises(self, AccessError):
                        action()
                    revision.invalidate_recordset()
                    self.assertEqual(revision.read(fields), before)

    def test_reviewer_and_administrator_return_require_bounded_reason(self):
        revision = self._revision(self._requirement())
        revision.action_submit()
        reviewer = revision.with_user(self.approver)
        before = reviewer.action_read_snapshot()
        for reason in (None, "", "   ", "x" * 4001):
            with self.assertRaises(ValidationError):
                reviewer.action_return_to_draft(reason)
            self.assertEqual(reviewer.action_read_snapshot(), before)
        action = reviewer.action_request_return()
        self.assertEqual(reviewer.action_read_snapshot(), before)
        wizard = (
            self.env[action["res_model"]]
            .with_user(self.approver)
            .with_context(**action["context"])
            .create({})
        )
        with self.assertRaises(ValidationError):
            wizard.action_confirm()
        self.assertEqual(reviewer.action_read_snapshot(), before)
        with Form(wizard) as form:
            form.reason = "  Reviewer asks for measurable expectations  "
        wizard.action_confirm()
        self.assertEqual(revision.state, "draft")
        self.assertEqual(
            revision.return_reason, "Reviewer asks for measurable expectations"
        )
        self.assertFalse(revision.snapshot_json)
        self.assertFalse(revision.snapshot_sha256)
        self.assertTrue(revision.requirement_revision_ids.sealed)
        # A different administrator may return, including their own submission.
        administrator = revision.with_user(self.administrator)
        administrator.action_submit()
        self.assertEqual(revision.submitted_by_id, self.administrator)
        self.assertNotEqual(revision.document_id.approver_id, self.administrator)
        administrator.action_return_to_draft("x" * 4000)
        self.assertEqual(revision.state, "draft")
        self.assertEqual(revision.return_reason, "x" * 4000)
        # Return authority does not broaden the designated-user approval boundary.
        administrator.action_submit()
        with self.assertRaises(AccessError):
            administrator.action_approve()
        reviewer.action_approve()

    def test_return_rechecks_project_company_and_active_reviewer(self):
        revision = self._revision(self._requirement())
        revision.action_submit()
        reviewer = revision.with_user(self.approver)
        action = reviewer.action_request_return()
        wizard = (
            self.env[action["res_model"]]
            .with_user(self.approver)
            .with_context(**action["context"])
            .create({"reason": "Opened before revocation"})
        )
        before = revision.action_read_snapshot()
        rule = self.env["ir.rule"].create(
            {
                "name": "Revoke reviewer Project",
                "model_id": self.env.ref("project.model_project_project").id,
                "domain_force": repr([("id", "!=", self.project.id)]),
            }
        )
        for operation in (
            reviewer.action_request_return,
            lambda: reviewer.action_return_to_draft("Revoked Project"),
            wizard.action_confirm,
        ):
            with self.assertRaises(AccessError):
                operation()
        rule.unlink()
        wrong_company = reviewer.with_context(
            allowed_company_ids=self.other_company.ids
        )
        for operation in (
            wrong_company.action_request_return,
            lambda: wrong_company.action_return_to_draft("Wrong company"),
            wizard.with_context(
                allowed_company_ids=self.other_company.ids
            ).action_confirm,
        ):
            with self.assertRaises(AccessError):
                operation()
        self.approver.active = False
        with self.assertRaises(AccessError):
            reviewer.action_return_to_draft("Inactive reviewer")
        self.approver.active = True
        revision.invalidate_recordset()
        self.assertEqual(revision.action_read_snapshot(), before)
        self.assertFalse(revision.return_reason)
        wizard.action_confirm()
        self.assertEqual(revision.state, "draft")

    def test_author_cannot_write_protected_state_or_acceptance(self):
        self.assertFalse(self.analyst.has_group("project.group_project_manager"))
        requirement = self._requirement()
        revision = self._revision(requirement)
        for values in (
            {"state": "approved"},
            {"approved_by_id": self.analyst.id},
            {"snapshot_json": "{}"},
        ):
            with self.assertRaises(ValidationError):
                revision.write(values)
        with self.assertRaises(ValidationError):
            revision.write({"_snapshot_content": "{}"})
        for values in ({"sealed": True}, {"number": 99}):
            with self.assertRaises(ValidationError):
                requirement.write(values)
        revision.action_submit()
        revision.with_user(self.approver).action_approve()
        acceptance = self.env["project.agile.requirement.acceptance"]
        values = {
            "requirement_revision_id": requirement.id,
            "document_revision_id": revision.id,
            "decision": "accepted",
            "authority_label": "Project approver",
            "criteria_evaluated": "Observed",
            "evidence": "Manual evaluation",
        }
        with self.assertRaises(AccessError):
            acceptance.with_user(self.analyst).create(dict(values))
        event = acceptance.with_user(self.approver).create(values)
        self.assertEqual(event.recorded_by_id, self.approver)
        with self.assertRaises(AccessError):
            event.with_user(self.analyst).write({"evidence": "Rewrite"})
        with self.assertRaises(AccessError):
            self.env["project.agile.solution.template"].with_user(self.analyst).create(
                {}
            )
        for model in (
            "project.agile.requirement",
            "project.agile.solution.document",
            "project.agile.solution.task.intent",
        ):
            with self.assertRaises(AccessError):
                self.env[model].with_user(self.member).create({})

    def test_author_scope_context_revocation_and_inactive_caller(self):
        self.assertFalse(self.analyst.has_group("project.group_project_manager"))
        for project in (self.hidden, self.foreign):
            solution = self.env["project.agile.solution"].create(
                {
                    "name": "Unavailable",
                    "project_id": project.id,
                }
            )
            with self.assertRaises(AccessError):
                self._requirement(solution)
            with self.assertRaises(AccessError):
                self.env["project.agile.solution"].with_user(self.analyst).create(
                    {
                        "name": "Bypass",
                        "project_id": project.id,
                    }
                )
            self.assertFalse(
                solution.with_user(self.analyst).search([("id", "=", solution.id)])
            )
        with self.assertRaises(AccessError):
            self.env["project.agile.solution"].with_user(self.analyst).with_context(
                allowed_company_ids=self.other_company.ids, sudo=True
            ).create({"name": "Forged company", "project_id": self.foreign.id})
        requirement = self._requirement()
        intent = self._preview(requirement)
        revision = self._revision(requirement)
        rule = self.env["ir.rule"].create(
            {
                "name": "Revoke BA Project",
                "model_id": self.env.ref("project.model_project_project").id,
                "domain_force": repr([("id", "!=", self.project.id)]),
            }
        )
        before = self.env["project.task"].search_count([])
        for action in (
            intent.action_confirm,
            revision.action_submit,
            requirement.requirement_id.action_new_revision,
        ):
            with self.assertRaises(AccessError):
                action()
        rule.unlink()
        self.assertEqual(intent.state, "preview")
        self.assertEqual(self.env["project.task"].search_count([]), before)
        self.analyst.active = False
        with self.assertRaises(AccessError):
            intent.action_confirm()
        with self.assertRaises(AccessError):
            requirement.write({"title": "Inactive"})

    def test_ba_refines_selected_link_without_project_administration(self):
        requirement = self._requirement()
        intent = self._preview(requirement)
        intent.action_confirm()
        link = (
            self.env["project.agile.requirement.task.link"]
            .with_user(self.analyst)
            .search(
                [
                    ("task_id", "=", intent.task_id.id),
                ]
            )
        )
        self.assertFalse(self.analyst.has_group("project.group_project_manager"))
        action = link.action_request_refinement()
        wizard = (
            self.env[action["res_model"]]
            .with_user(self.analyst)
            .browse(action["res_id"])
        )
        with Form(wizard) as form:
            form.acceptance_expectations = "BA can refine without approving scope"
        wizard.action_confirm()
        self.assertIn(
            "BA can refine without approving scope",
            intent.task_id.solution_requirement_acceptance,
        )
        self.assertFalse(link.active)

"""Two real clients, exact revisions and native revocation paths, not ACL mocks."""

import json

from odoo import Command
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.mail.tests.common import mail_new_test_user

from .test_solution_requirements import TestSolutionRequirements


class TestSolutionPortal(TestSolutionRequirements):
    def setUp(self):
        super().setUp()
        self.client = mail_new_test_user(
            self.env,
            "solution_client_a",
            groups="base.group_portal,base.group_allow_export",
            company_ids=[Command.set((self.company | self.other_company).ids)],
            company_id=self.other_company.id,
        )
        self.client_b = mail_new_test_user(
            self.env,
            "solution_client_b",
            groups="base.group_portal,base.group_allow_export",
        )
        self.project.write({"privacy_visibility": "portal"})
        self.project.message_subscribe(partner_ids=self.client.partner_id.ids)
        self.document.write({"portal_approver_id": self.client.id})
        self.requirement = self._requirement(
            audience="customer", rationale="PRIVATE rationale"
        )
        hidden = self._requirement(title="PRIVATE requirement")
        self.baseline = self._revision(
            requirement_revision_ids=[Command.set((self.requirement | hidden).ids)],
            section_ids=[
                Command.create(
                    {
                        "title": "Customer scope",
                        "audience": "customer",
                        "body": "<p>Disclosed scope.</p><img src='https://example.invalid/private'/>",
                    }
                ),
                Command.create(
                    {"title": "PRIVATE section", "body": "PRIVATE narrative"}
                ),
            ],
            context_revision_ids=[
                Command.set(
                    self._context(
                        "deliverable",
                        audience="customer",
                        affected_requirement_revision_ids=[
                            Command.set((self.requirement | hidden).ids)
                        ],
                    ).ids
                )
            ],
        )
        self._approve(self.baseline)
        self.publication = self._issue()
        project_b = self._project(
            "Client B", "SYNCLIENTB", self.company, privacy="portal"
        )
        project_b.message_subscribe(partner_ids=self.client_b.partner_id.ids)
        solution_b = (
            self.env["project.agile.solution"]
            .with_user(self.manager)
            .create(
                {
                    "name": "PRIVATE client B solution",
                    "project_id": project_b.id,
                }
            )
        )
        document_b = self.document.create(
            {
                "name": "PRIVATE client B document",
                "solution_id": solution_b.id,
                "portal_approver_id": self.client_b.id,
            }
        )
        baseline_b = self._revision(
            document=document_b, title="PRIVATE client B content"
        )
        self._approve(baseline_b)
        self.publication_b = (
            self.env[self.publication._name]
            .browse(baseline_b.action_issue_portal(self.client_b.id))
            .with_user(self.client_b)
        )

    def _issue(self):
        return (
            self.env["project.agile.solution.portal.publication"]
            .browse(self.baseline.action_issue_portal(self.client.id))
            .with_user(self.client)
        )

    def _accept(self, publication=None, **values):
        return (publication or self.publication).action_decide_requirement(
            **{
                "key": self.requirement.requirement_id.key,
                "number": self.requirement.number,
                "decision": "accepted",
                "criteria_evaluated": "Own request identity matrix",
                "evidence": "Observed own request",
                **values,
            }
        )

    def _assert_denied(self, publication):
        model = publication.with_context(active_test=False)
        domain = [("id", "=", publication.id)]
        self.assertFalse(model.search(domain))
        self.assertEqual(model.search_count(domain), 0)
        self.assertEqual(model._read_group(domain, ["name"], ["__count"]), [])
        self.assertFalse(model.name_search("SYNTHETIC", domain))
        for action in (
            lambda: model.read(["name", "payload_json"]),
            lambda: model.export_data(["payload_json"]),
            model.action_view,
            lambda: model.action_decide_document("approved"),
        ):
            with self.assertRaises(AccessError):
                action()

    def test_two_clients_search_read_group_export_and_raw_source_isolation(self):
        self.assertEqual(self.publication.search([]), self.publication)
        self.assertEqual(self.publication_b.search([]), self.publication_b)
        self._assert_denied(self.publication_b.with_user(self.client))
        payload = self.publication.read(["payload_json"])[0]["payload_json"]
        self.assertNotIn("PRIVATE", payload)
        self.assertNotIn("revision_id", payload)
        self.assertNotIn("example.invalid", payload)
        self.assertEqual(len(json.loads(payload)["contexts"][0]["requirements"]), 1)
        for field in ("revision_id", "recipient_id", "snapshot_sha256", "_member_map"):
            with self.assertRaises(AccessError):
                self.publication.read([field])
            with self.assertRaises(AccessError):
                self.publication.export_data([field])
        for row in (self.baseline, self.requirement, self.document, self.solution):
            with self.assertRaises(AccessError):
                row.with_user(self.client).read(["display_name"])
        with self.assertRaises(AccessError):
            self.baseline.with_user(self.client).sudo().action_projection("customer")
        with self.assertRaises(AccessError):
            self.baseline.with_user(self.client).action_approve()

    def test_commercial_sibling_visibility_is_not_signing_or_disclosure(self):
        parent = self.env["res.partner"].create(
            {"name": "Shared commercial customer", "is_company": True}
        )
        self.client.partner_id.write({"parent_id": parent.id})
        sibling = mail_new_test_user(
            self.env, "solution_sibling", groups="base.group_portal"
        )
        sibling.partner_id.write({"parent_id": parent.id})
        self.publication = self._issue()
        self.project.with_user(sibling).check_access("read")
        self._assert_denied(self.publication.with_user(sibling))
        self.project.message_subscribe(partner_ids=sibling.partner_id.ids)
        viewer = (
            self.env[self.publication._name]
            .browse(self.baseline.action_issue_portal(sibling.id))
            .with_user(sibling)
        )
        self.assertTrue(viewer.action_view()["payload"])
        self.assertFalse(viewer.action_view()["can_decide"])
        with self.assertRaises(AccessError):
            viewer.action_decide_document("approved")
        self.assertTrue(self.publication.action_decide_document("approved"))

    def test_audit_exactness_stale_correction_and_distinct_proxy_channel(self):
        first = self.publication.action_decide_document(
            "rejected", comment="Customer scope correction"
        )
        self.assertEqual(self.baseline.state, "approved")
        with self.assertRaises(ValidationError):
            self.publication.action_decide_document("approved")
        second = self.publication.action_decide_document("approved", first["id"])
        event = self.env["project.agile.solution.portal.document.decision"].browse(
            second["id"]
        )
        self.assertEqual(event.actor_id, self.client)
        self.assertEqual(event.partner_id, self.client.partner_id)
        self.assertEqual(event.supersedes_id.id, first["id"])
        self.assertEqual(event.payload_sha256, self.publication.payload_sha256)
        self.assertTrue(event.recorded_at)
        accepted = self._accept()
        with self.assertRaises(ValidationError):
            self._accept()
        portal = self.env["project.agile.requirement.acceptance"].browse(accepted["id"])
        proxy = (
            self.env[portal._name]
            .with_user(self.manager)
            .create(
                {
                    "requirement_revision_id": self.requirement.id,
                    "document_revision_id": self.baseline.id,
                    "decision": "accepted",
                    "authority_label": "Internal assertion",
                    "criteria_evaluated": "Proxy matrix",
                    "evidence": "Internal proxy evidence",
                }
            )
        )
        self.assertEqual(proxy.decision_source, "internal_proxy")
        self.assertFalse(proxy.supersedes_id)
        self.assertEqual(portal.recorded_by_id, self.client)
        self.assertEqual(portal.decision_source, "portal")
        self.assertEqual(portal.publication_id.id, self.publication.id)
        self.assertEqual(portal.portal_partner_id, self.client.partner_id)
        corrected = self._accept(decision="rejected", expected_event_id=accepted["id"])
        self.assertEqual(
            self.env[portal._name].browse(corrected["id"]).supersedes_id, portal
        )
        coverage = self.baseline.action_coverage()["categories"]
        self.assertEqual(
            coverage["accepted_with_evidence"][0]["evidence"], proxy.evidence
        )
        self.assertEqual(len(coverage["authenticated_client_decisions"]), 1)
        self.assertEqual(len(coverage["authenticated_client_history"]), 2)
        self.assertNotIn(
            "Internal proxy evidence", json.dumps(self.publication.action_view())
        )
        for row in (event, portal):
            with self.assertRaises(AccessError):
                row.sudo().write({"decision": "rejected"})
            with self.assertRaises(
                AccessError if row._name == event._name else ValidationError
            ):
                row.sudo().unlink()
            with self.assertRaises(
                AccessError if row._name == event._name else ValidationError
            ):
                row.sudo().copy()

    def test_forged_member_actor_defaults_and_direct_creates_fail_before_append(self):
        for values in (
            {"key": "FOREIGN"},
            {"number": True},
            {"number": 999},
            {"decision": "withdrawn"},
            {"criteria_evaluated": ""},
            {"evidence": ""},
            {"expected_event_id": True},
        ):
            with self.assertRaises(AccessError if "key" in values else ValidationError):
                self._accept(**values)
        for name in (
            "default_recorded_by_id",
            "default_decision_source",
            "default_publication_id",
        ):
            with self.assertRaises(ValidationError):
                self.publication.with_context(
                    **{name: self.client_b.id}
                ).action_decide_document("approved")
        for model in (
            "project.agile.solution.portal.document.decision",
            self.publication._name,
            "project.agile.requirement.acceptance",
        ):
            with self.assertRaises(AccessError):
                self.env[model].with_user(self.client).sudo().create(
                    {"decision": "approved"}
                )
        self.assertFalse(self.publication.action_view()["document"]["id"])
        self.assertFalse(self.env["project.agile.requirement.acceptance"].search([]))
        self.assertTrue(self.publication_b.action_decide_document("approved"))

    def test_native_follower_revocation_reinvite_and_explicit_reissue(self):
        self.publication.action_view()
        self.project.message_unsubscribe(partner_ids=self.client.partner_id.ids)
        self._assert_denied(self.publication)
        self.assertTrue(self.publication_b.action_view()["can_decide"])
        self.project.message_subscribe(partner_ids=self.client.partner_id.ids)
        self._assert_denied(self.publication)
        replacement = self._issue()
        self.assertNotEqual(replacement.id, self.publication.id)
        self.assertTrue(replacement.action_decide_document("approved"))

    def test_native_identity_company_group_partner_and_designation_revocations(self):
        def archive_contact():
            # Native Odoo refuses archiving a contact while its user is active.
            self.client.write({"active": False})
            self.client.partner_id.write({"active": False})

        operations = (
            lambda: self.client.write({"active": False}),
            archive_contact,
            lambda: self.client.write({"partner_id": self.client_b.partner_id.id}),
            lambda: self.client.write(
                {
                    "company_ids": [Command.set(self.other_company.ids)],
                    "company_id": self.other_company.id,
                }
            ),
            lambda: self.env.ref("base.group_portal").write(
                {"user_ids": [Command.unlink(self.client.id)]}
            ),
            lambda: self.document.write({"portal_approver_id": False}),
            lambda: self.company.write({"user_ids": [Command.unlink(self.client.id)]}),
        )
        for index, operation in enumerate(operations):
            # Exercise supported native lifecycle changes on independent live
            # identities, not restoration through test-only security rollbacks.
            self.client = mail_new_test_user(
                self.env,
                "solution_revoke_" + str(index),
                groups="base.group_portal",
                company_ids=[Command.set((self.company | self.other_company).ids)],
                company_id=self.other_company.id,
            )
            self.project.message_subscribe(partner_ids=self.client.partner_id.ids)
            self.document.write({"portal_approver_id": self.client.id})
            self.publication = self._issue()
            self.assertTrue(self.publication.action_view()["can_decide"])
            operation()
            self.assertTrue(self.publication.sudo().revoked_at)
            self.assertTrue(self.publication_b.action_view()["can_decide"])
            with self.assertRaises(AccessError):
                self.publication.action_decide_document("approved")
        self.assertTrue(self.publication_b.action_decide_document("approved"))

    def test_supersession_keeps_history_no_carryover_and_archives_deny_read(self):
        first = self.publication.action_decide_document("approved")
        accepted = self._accept()
        successor = self.baseline.browse(self.baseline.action_new_revision()["res_id"])
        self.assertTrue(self.publication.action_view()["current"])
        self._approve(successor)
        view = self.publication.action_view()
        self.assertFalse(view["current"])
        self.assertEqual(view["document"]["id"], first["id"])
        with self.assertRaises(AccessError):
            self._accept(expected_event_id=accepted["id"])
        fresh = (
            self.env[self.publication._name]
            .browse(successor.action_issue_portal(self.client.id))
            .with_user(self.client)
        )
        self.assertFalse(fresh.action_view()["document"]["id"])
        self.assertFalse(
            fresh.action_view()["requirements"][self.requirement.requirement_id.key][
                "id"
            ]
        )
        for row in (self.project, self.solution.with_user(self.manager), self.document):
            row.write({"active": False})
            self._assert_denied(fresh)
            row.write({"active": True})
        self.assertTrue(fresh.action_decide_document("approved"))

    def test_ba_cannot_designate_publish_or_revoke_and_protected_default_is_ignored(
        self,
    ):
        analyst = mail_new_test_user(
            self.env,
            "solution_client_ba",
            groups="project_agile_solution.group_business_analyst",
        )
        for action in (
            lambda: self.document.with_user(analyst).write(
                {"portal_approver_id": self.client_b.id}
            ),
            lambda: self.baseline.with_user(analyst).action_issue_portal(
                self.client.id
            ),
            lambda: self.publication.with_user(analyst).action_revoke(),
        ):
            with self.assertRaises(AccessError):
                action()
        self.assertNotIn(
            "portal_approver_id",
            self.document.with_user(analyst)
            .with_context(default_portal_approver_id=self.client.id)
            .default_get(["portal_approver_id"]),
        )

    def test_current_native_project_rule_and_companyless_publication(self):
        rule = self._hide("project.project", self.project)
        self._assert_denied(self.publication)
        self.assertTrue(self.publication_b.action_view()["can_decide"])
        rule.unlink()
        project = self._project(
            "Companyless client",
            "SYNPORTALSHARED",
            self.env["res.company"],
            privacy="portal",
        )
        project.message_subscribe(partner_ids=self.client.partner_id.ids)
        solution = (
            self.env["project.agile.solution"]
            .with_user(self.manager)
            .create(
                {
                    "name": "Shared companyless initiative",
                    "project_id": project.id,
                }
            )
        )
        document = self.document.create(
            {"name": "Shared brief", "solution_id": solution.id}
        )
        baseline = self._revision(document=document)
        self._approve(baseline)
        document.write({"portal_approver_id": self.client.id})
        publication = (
            self.env[self.publication._name]
            .browse(baseline.action_issue_portal(self.client.id))
            .with_user(self.client)
        )
        self.assertTrue(publication.action_decide_document("approved"))

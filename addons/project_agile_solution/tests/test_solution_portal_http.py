"""Actual authenticated HTTP/CSRF/RPC and two independent client browser journeys."""

import copy
import json
from pathlib import Path

from lxml import html

from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user

from .solution_fixture import seed_scenario
from .test_solution_render_tour import TestSolutionRenderTour


@tagged("post_install", "-at_install")
class TestSolutionPortalHttp(HttpCase):
    _rpc = TestSolutionRenderTour._rpc

    def setUp(self):
        super().setUp()
        manager = mail_new_test_user(
            self.env, "solution_http_manager", groups="project.group_project_manager"
        )
        scenario = json.loads(
            (Path(__file__).parent / "fixtures/synthetic_scenarios.json").read_text()
        )["scenarios"][0]
        self.clients, self.publications, self.scopes = [], [], []
        for suffix in ("A", "B"):
            client = mail_new_test_user(
                self.env, "solution_http_" + suffix, groups="base.group_portal"
            )
            source = copy.deepcopy(scenario)
            source["project_key"] = "SYNHTTP" + suffix
            source["project_name"] = "CLIENT " + suffix + " DISCLOSURE"
            source["requirements"][0]["rationale"] = "PRIVATE_HTTP rationale"
            source["requirements"][0]["text"] += (
                ' <img src=x onerror="window.solutionInjected=true">'
            )
            seeded = seed_scenario(self.env, manager, self.env.company, source)
            seeded["project"].write({"privacy_visibility": "portal"})
            seeded["project"].message_subscribe(partner_ids=client.partner_id.ids)
            seeded["spec"].document_id.write({"portal_approver_id": client.id})
            publication = self.env["project.agile.solution.portal.publication"].browse(
                seeded["spec"].action_issue_portal(client.id)
            )
            self.clients.append(client)
            self.publications.append(publication)
            self.scopes.append(seeded)

    def _url(self, index=0):
        return f"/my/solution-documents/{self.publications[index].id}"

    def _token(self, response):
        return html.fromstring(response.content).xpath(
            "//input[@name='csrf_token']/@value"
        )[0]

    def test_native_http_two_client_download_csrf_forgery_rpc_and_revoke(self):
        client = self.clients[0]
        self.authenticate(client.login, client.login)
        page = self.url_open(self._url())
        self.assertEqual(page.status_code, 200)
        self.assertIn("CLIENT A DISCLOSURE", page.text)
        self.assertNotIn("PRIVATE_HTTP", page.text)
        self.assertNotIn(
            "CLIENT B DISCLOSURE", self.url_open("/my/solution-documents").text
        )
        self.assertIn(
            "CLIENT A DISCLOSURE", self.url_open(self._url() + "/download").text
        )
        for suffix in ("", "/download"):
            denied = self.url_open(self._url(1) + suffix)
            self.assertEqual(denied.status_code, 404)
            self.assertNotIn("CLIENT B DISCLOSURE", denied.text)
        token = self._token(page)
        values = {"kind": "document", "decision": "approved", "expected_event_id": ""}
        for forged in (
            {},
            {"csrf_token": "wrong"},
            {"csrf_token": token, "actor_id": self.clients[1].id},
        ):
            response = self.url_open(
                self._url() + "/decision", data={**values, **forged}
            )
            self.assertEqual(response.status_code, 400)
        self.assertFalse(self.publications[0].document_decision_ids)
        unsafe = self.url_open(self._url() + "/decision")
        self.assertIn(unsafe.status_code, (404, 405))
        for method, args in (
            ("action_decide_document", [[self.publications[1].id], "approved"]),
            ("read", [[self.publications[0].id], ["revision_id"]]),
            (
                "action_decide_requirement",
                [
                    [self.publications[0].id],
                    "FORGED",
                    1,
                    "accepted",
                    "criteria",
                    "evidence",
                ],
            ),
        ):
            result = self._rpc(self.publications[0]._name, method, args, {"sudo": True})
            self.assertIn("error", result)
        created = self.url_open(
            self._url() + "/decision", data={**values, "csrf_token": token}
        )
        self.assertEqual(created.status_code, 200)
        self.assertIn("approved", created.text)
        event = self.publications[0].document_decision_ids
        self.assertEqual(len(event), 1)
        self.assertEqual(event.actor_id, client)
        self.assertTrue(event.recorded_at)
        stale = self.url_open(
            self._url() + "/decision", data={**values, "csrf_token": token}
        )
        self.assertEqual(stale.status_code, 400)
        self.scopes[0]["project"].message_unsubscribe(partner_ids=client.partner_id.ids)
        self.env.flush_all()
        revoked = self.url_open(
            self._url() + "/decision", data={**values, "csrf_token": token}
        )
        self.assertEqual(revoked.status_code, 404)
        self.assertEqual(len(self.publications[0].document_decision_ids), 1)
        other = self.clients[1]
        self.authenticate(other.login, other.login)
        self.assertEqual(self.url_open(self._url(1)).status_code, 200)
        self.assertEqual(self.url_open(self._url()).status_code, 404)
        self.authenticate(None, None)
        project = self.scopes[1]["project"]
        project._portal_ensure_token()
        public = self.url_open(self._url(1) + "?access_token=" + project.access_token)
        self.assertNotIn("CLIENT B DISCLOSURE", public.text)
        self.assertEqual(len(self.publications[1].document_decision_ids), 0)

    def test_http_reissue_and_signer_replacement_start_with_own_empty_receipts(self):
        spec = self.scopes[0]["spec"]
        requirement = self.scopes[0]["requirements"]["FR1"]
        client_a, client_b = self.clients
        original = self.publications[0]
        caller = original.with_user(client_a)
        self.assertFalse(caller.env.su)
        document = caller.action_decide_document(
            "approved", comment="FORMER SIGNER NOTE"
        )
        accepted = caller.action_decide_requirement(
            requirement.requirement_id.key,
            requirement.number,
            "accepted",
            "Former criteria",
            "FORMER SIGNER EVIDENCE",
        )
        before_b = self.publications[1].with_user(client_b).action_view()
        self.authenticate(client_a.login, client_a.login)
        page = self.url_open(self._url())
        self.assertEqual(page.status_code, 200)
        self.assertIn("FORMER SIGNER NOTE", page.text)
        old_token = self._token(page)
        old_url = self._url()
        self.publications[0] = original.browse(spec.action_issue_portal(client_a.id))
        page = self.url_open(self._url())
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("FORMER SIGNER", page.text)
        self.assertIn("No client decision recorded.", page.text)
        self.assertTrue(
            any(
                "o_solution_document_decision" in form.classes
                for form in html.fromstring(page.content).xpath("//form")
            )
        )
        self.assertEqual(
            spec.action_coverage()["categories"]["authenticated_client_decisions"], []
        )
        self.assertEqual(self.url_open(old_url).status_code, 404)
        self.assertEqual(
            self.url_open(
                old_url + "/decision",
                data={
                    "csrf_token": old_token,
                    "kind": "document",
                    "decision": "rejected",
                    "expected_event_id": str(document["id"]),
                },
            ).status_code,
            404,
        )

        self.scopes[0]["project"].message_subscribe(partner_ids=client_b.partner_id.ids)
        spec.document_id.write({"portal_approver_id": client_b.id})
        reissued_url = self._url()
        self.publications[0] = original.browse(spec.action_issue_portal(client_b.id))
        self.authenticate(client_b.login, client_b.login)
        self.assertEqual(self.url_open(reissued_url).status_code, 404)
        page = self.url_open(self._url())
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("FORMER SIGNER", page.text)
        self.assertIn("No client decision recorded.", page.text)
        self.assertEqual(
            spec.action_coverage()["categories"]["authenticated_client_decisions"], []
        )
        token = self._token(page)
        decided = self.url_open(
            self._url() + "/decision",
            data={
                "csrf_token": token,
                "kind": "requirement",
                "decision": "accepted",
                "key": requirement.requirement_id.key,
                "number": str(requirement.number),
                "criteria_evaluated": "Replacement criteria",
                "evidence": "REPLACEMENT EVIDENCE",
                "expected_event_id": "",
            },
        )
        self.assertEqual(decided.status_code, 200)
        self.assertIn("REPLACEMENT EVIDENCE", decided.text)
        self.assertNotIn("FORMER SIGNER", decided.text)
        receipt = (
            self.publications[0]
            .with_user(client_b)
            .action_view()["requirements"][requirement.requirement_id.key]
        )
        coverage = spec.action_coverage()["categories"]
        self.assertEqual(
            [row["id"] for row in coverage["authenticated_client_decisions"]],
            [receipt["id"]],
        )
        self.assertEqual(
            [row["id"] for row in coverage["authenticated_client_history"]],
            [receipt["id"], accepted["id"]],
        )
        self.assertEqual(original.document_decision_ids.ids, [document["id"]])
        self.assertEqual(original.document_decision_ids.actor_id, client_a)
        self.assertEqual(
            self.publications[1].with_user(client_b).action_view(), before_b
        )
        self.assertEqual(self.url_open(self._url(1)).status_code, 200)
        self.authenticate(client_a.login, client_a.login)
        self.assertEqual(self.url_open(self._url()).status_code, 404)

    def test_real_two_client_browser_decisions_receipts_and_escaped_content(self):
        for index, client in enumerate(self.clients):
            self.start_tour(
                self._url(index), "solution_client_decisions", login=client.login
            )
            foreign = "CLIENT B DISCLOSURE" if index == 0 else "CLIENT A DISCLOSURE"
            self.browser_js(
                "/my/solution-documents",
                f"""
                if (document.body.textContent.includes({json.dumps(foreign)})) {{
                    throw new Error('Foreign publication label on client list');
                }}
                console.log('test successful');
            """,
                login=client.login,
                ready="!!document.querySelector('.o_solution_publications')",
            )
            document = self.publications[index].document_decision_ids.sorted("id")
            self.assertEqual(document.mapped("decision"), ["rejected", "approved"])
            self.assertEqual(document.actor_id, client)
            acceptance = self.env["project.agile.requirement.acceptance"].search(
                [("publication_id", "=", self.publications[index].id)], order="id"
            )
            self.assertEqual(acceptance.mapped("decision"), ["accepted", "rejected"])
            self.assertEqual(acceptance.recorded_by_id, client)
            self.assertEqual(
                acceptance.requirement_revision_id,
                self.scopes[index]["requirements"]["FR1"],
            )
            report = (
                "/report/html/project_agile_solution.report_solution_customer/"
                + str(self.scopes[index]["spec"].id)
            )
            self.authenticate(client.login, client.login)
            denied = self.url_open(report)
            self.assertEqual(denied.status_code, 403)

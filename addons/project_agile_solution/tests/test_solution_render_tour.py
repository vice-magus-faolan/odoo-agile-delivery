"""Native browser preview/report journeys for all three synthetic narratives."""

import copy
import json
from pathlib import Path

from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user

from .solution_fixture import seed_scenario


@tagged("post_install", "-at_install")
class TestSolutionRenderTour(HttpCase):
    def setUp(self):
        super().setUp()
        self.manager = mail_new_test_user(
            self.env, "solution_tour_manager", groups="project.group_project_manager"
        )
        self.reader = mail_new_test_user(
            self.env,
            "solution_tour_reader",
            groups="project.group_project_user,base.group_allow_export",
        )
        self.scenarios = json.loads(
            (Path(__file__).parent / "fixtures/synthetic_scenarios.json").read_text()
        )["scenarios"]

    def test_three_native_form_audience_and_direct_report_browser_journeys(self):
        for scenario in self.scenarios:
            scenario = copy.deepcopy(scenario)
            scenario["requirements"][0]["text"] += (
                ' <img src=x onerror="window.solutionInjected=true">'
            )
            seeded = seed_scenario(self.env, self.manager, self.env.company, scenario)
            # Add explicit private content on a separate working revision;
            # preview must not alias the approved baseline to this newer row.
            draft = seeded["spec"].browse(
                seeded["spec"].action_new_revision()["res_id"]
            )
            draft.write(
                {
                    "section_ids": [
                        Command.create(
                            {
                                "title": "SECRET TOUR",
                                "body": "<p>SECRET TOUR narrative</p>",
                            }
                        )
                    ]
                }
            )
            action_id = self.env.ref(
                "project_agile_solution.action_solution_revision"
            ).id
            self.start_tour(
                f"/odoo/action-{action_id}/{draft.id}",
                "solution_exact_preview",
                login=self.reader.login,
            )
            report = (
                "/report/html/project_agile_solution.report_solution_customer/"
                f"{seeded['spec'].id}"
            )
            self.browser_js(
                report,
                """
                if (!document.querySelector('.o_solution_projection')) {
                    throw new Error('Missing native QWeb projection');
                }
                if (!document.body.textContent.includes('Redacted customer projection')
                    || document.body.textContent.includes('SECRET TOUR')) {
                    throw new Error('Wrong audience or hidden narrative '
                        + 'on direct native report route');
                }
                if (document.body.textContent.includes('Unapproved working')) {
                    throw new Error('Report substituted a moving draft '
                        + 'for exact baseline');
                }
                if (window.solutionInjected
                    || document.querySelector('.o_solution_projection img[src="x"]')) {
                    throw new Error('Native report executed injected '
                        + 'requirement markup');
                }
                console.log('test successful');
            """,
                login=self.reader.login,
                ready="!!document.querySelector('.o_solution_projection')",
            )

    def test_native_report_http_denies_now_inaccessible_project_and_public(self):
        seeded = seed_scenario(
            self.env, self.manager, self.env.company, self.scenarios[0]
        )
        baseline = seeded["spec"]
        scenario_title = seeded["requirements"]["FR1"].title
        url = (
            "/report/html/project_agile_solution.report_solution_customer/"
            f"{baseline.id}"
        )
        self.authenticate(self.reader.login, self.reader.login)
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Redacted customer projection", response.text)
        self.env["ir.rule"].create(
            {
                "name": "SYNTHETIC report project denial",
                "model_id": self.env["ir.model"]._get_id("project.project"),
                "domain_force": repr([("id", "!=", seeded["project"].id)]),
            }
        )
        self.env.flush_all()
        denied = self.url_open(url)
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(scenario_title, denied.text)
        self.assertNotIn("Redacted customer projection", denied.text)
        self.authenticate(None, None)
        public = self.url_open(url)
        self.assertNotIn(scenario_title, public.text)

    def _rpc(self, model, method, args, context=None):
        """Exercise the exact Odoo 19 authenticated dataset JSON-RPC route."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": {"context": context or {}},
            },
        }
        response = self.url_open(
            "/web/dataset/call_kw",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_native_jsonrpc_hidden_closure_export_and_action_bypass_negatives(self):
        seeded = seed_scenario(
            self.env, self.manager, self.env.company, self.scenarios[0]
        )
        baseline, requirement = seeded["spec"], seeded["requirements"]["FR1"]
        self.authenticate(self.reader.login, self.reader.login)
        model = baseline._name
        allowed = self._rpc(model, "action_projection", [baseline.ids, "customer"])
        self.assertIn("requirements", allowed["result"])
        acceptance = self._rpc(
            "project.agile.requirement.acceptance",
            "create",
            [
                {
                    "document_revision_id": baseline.id,
                    "requirement_revision_id": requirement.id,
                    "decision": "accepted",
                    "authority_label": "SYNTHETIC forged reader authority",
                    "criteria_evaluated": "SYNTHETIC forged criteria",
                    "evidence": "SYNTHETIC forged evidence",
                }
            ],
            {"sudo": True, "solution_trusted": True},
        )
        self.assertEqual(
            acceptance["error"]["data"]["name"], "odoo.exceptions.AccessError"
        )
        self.assertFalse(
            self.env["project.agile.requirement.acceptance"].search(
                [("document_revision_id", "=", baseline.id)]
            )
        )
        hidden_description = requirement.description
        self.env["ir.rule"].create(
            {
                "name": "SYNTHETIC RPC hidden exact requirement",
                "model_id": self.env["ir.model"]._get_id(requirement._name),
                "domain_force": repr([("id", "!=", requirement.id)]),
            }
        )
        self.env.flush_all()
        context = {
            "sudo": True,
            "solution_trusted": True,
            "skip_immutability": True,
            "default_state": "approved",
            "audience": "internal",
        }
        calls = [
            ("read", [baseline.ids, ["snapshot_json"]]),
            ("export_data", [baseline.ids, ["snapshot_json"]]),
            ("action_read_snapshot", [baseline.ids]),
            ("action_projection", [baseline.ids, "customer"]),
            ("action_coverage", [baseline.ids]),
            ("action_approve", [baseline.ids]),
        ]
        for method, args in calls:
            with self.subTest(method=method):
                denied = self._rpc(model, method, args, context)
                self.assertNotIn("result", denied)
                self.assertEqual(
                    denied["error"]["data"]["name"], "odoo.exceptions.AccessError"
                )
                self.assertNotIn(hidden_description, json.dumps(denied))
        self.assertEqual(baseline.state, "approved")

    def test_business_analyst_native_submit_and_rpc_approval_refusal(self):
        analyst = mail_new_test_user(
            self.env,
            "solution_tour_analyst",
            groups="project_agile_solution.group_business_analyst",
        )
        self.assertFalse(analyst.has_group("project.group_project_manager"))
        seeded = seed_scenario(
            self.env, self.manager, self.env.company, self.scenarios[0]
        )
        draft = seeded["spec"].browse(seeded["spec"].action_new_revision()["res_id"])
        action_id = self.env.ref("project_agile_solution.action_solution_revision").id
        self.start_tour(
            f"/odoo/action-{action_id}/{draft.id}",
            "solution_author_roles",
            login=analyst.login,
        )
        self.authenticate(analyst.login, analyst.login)
        before = draft.action_read_snapshot()
        for method, args in (
            ("action_approve", [draft.ids]),
            ("action_request_return", [draft.ids]),
            ("action_return_to_draft", [draft.ids, "Forged review decision"]),
        ):
            denied = self._rpc(draft._name, method, args, {"sudo": True})
            self.assertEqual(
                denied["error"]["data"]["name"], "odoo.exceptions.AccessError"
            )
            draft.invalidate_recordset()
            self.assertEqual(draft.action_read_snapshot(), before)
        self.assertEqual(draft.state, "review")

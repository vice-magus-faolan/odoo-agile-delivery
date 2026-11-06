"""Native shared Stories, exact contact boundaries and one stable mail thread."""

import json

from lxml import html
from markupsafe import Markup

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user

from .test_solution_discussion import TestSolutionDiscussion
from .test_solution_render_tour import TestSolutionRenderTour


class CustomerRequirementFixture:
    def setUp(self):
        super().setUp()
        self.manager = mail_new_test_user(
            self.env,
            "customer_requirement_manager",
            groups="project.group_project_manager",
        )
        self.analyst = mail_new_test_user(
            self.env,
            "customer_requirement_ba",
            groups="project_agile_solution.group_business_analyst",
        )
        self.clients, self.projects, self.tasks, self.links, self.private_links = (
            [],
            [],
            [],
            [],
            [],
        )
        for suffix in ("A", "B"):
            client = mail_new_test_user(
                self.env,
                "customer_requirement_" + suffix,
                groups="base.group_portal,base.group_allow_export",
            )
            env = self.env["project.project"].with_user(self.manager).env
            project = env["project.project"].create(
                {
                    "name": "Customer Project " + suffix,
                    "agile_key": "SYNCRQ" + suffix,
                    "agile_enabled": True,
                    "privacy_visibility": "portal",
                    "company_id": self.env.company.id,
                    "partner_id": client.partner_id.id,
                }
            )
            project.message_subscribe(partner_ids=client.partner_id.ids)
            env["project.share.wizard"].create(
                {
                    "res_model": "project.project",
                    "res_id": project.id,
                    "collaborator_ids": [
                        Command.create(
                            {
                                "partner_id": client.partner_id.id,
                                "access_mode": "edit",
                            }
                        )
                    ],
                }
            )
            task = env["project.task"].create(
                {
                    "name": "Customer Story " + suffix,
                    "project_id": project.id,
                    "agile_item_type_id": env.ref(
                        "project_agile.project_agile_item_type_story"
                    ).id,
                }
            )
            task.message_subscribe(partner_ids=client.partner_id.ids)
            solution = env["project.agile.solution"].create(
                {
                    "name": "PRIVATE_SOLUTION_" + suffix,
                    "project_id": project.id,
                }
            )
            links = []
            for audience in ("customer", "internal"):
                identity = env["project.agile.requirement"].create(
                    {
                        "name": "PRIVATE_IDENTITY_" + suffix,
                        "solution_id": solution.id,
                    }
                )
                revision = env["project.agile.requirement.revision"].create(
                    {
                        "requirement_id": identity.id,
                        "title": "Customer intent " + suffix
                        if audience == "customer"
                        else "PRIVATE_INTENT",
                        "description": "Projected description " + suffix,
                        "rationale": "PRIVATE_RATIONALE",
                        "audience": audience,
                        "verification_method": "Demonstrate both user outcomes",
                        "acceptance_expectations": "Own request only",
                    }
                )
                links.append(
                    env["project.agile.requirement.task.link"].create(
                        {
                            "task_id": task.id,
                            "requirement_revision_id": revision.id,
                        }
                    )
                )
            identity = links[0].requirement_revision_id.requirement_id
            identity.message_post(
                body="PRIVATE_HISTORY",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            identity.message_post(body="PRIVATE_NOTE", subtype_xmlid="mail.mt_note")
            self.clients.append(client)
            self.projects.append(project)
            self.tasks.append(task)
            self.links.append(links[0])
            self.private_links.append(links[1])
        self.outsider = mail_new_test_user(
            self.env, "customer_requirement_outsider", groups="base.group_portal"
        )
        self.sibling = mail_new_test_user(
            self.env, "customer_requirement_sibling", groups="base.group_portal"
        )
        self.sibling.partner_id.parent_id = self.clients[0].partner_id

    def _thread(self, index=0):
        return self.links[index].requirement_revision_id.requirement_id

    def _shared_messages(self, index=0):
        return self.env["mail.message"].search(
            [
                ("model", "=", "project.agile.requirement"),
                ("res_id", "=", self._thread(index).id),
                (
                    "subtype_id",
                    "=",
                    self.env.ref("project_agile_solution.mt_requirement_customer").id,
                ),
            ],
            order="id",
        )

    def _reply_as_analyst(self, text):
        action = (
            self._thread().with_user(self.analyst).action_compose_customer_discussion()
        )
        composer = (
            self.env["mail.compose.message"]
            .with_user(self.analyst)
            .with_context(
                action["context"],
                mail_notify_force_send=False,
            )
            .create({"body": Markup("<p>%s</p>") % text})
        )
        composer.action_send_mail()


@tagged("post_install", "-at_install")
class TestCustomerRequirements(CustomerRequirementFixture, TransactionCase):
    _private_payloads = TestSolutionDiscussion._private_payloads
    _assert_payload_hidden = TestSolutionDiscussion._assert_payload_hidden

    def test_customer_projection_and_explicit_history_only(self):
        env = self._thread().env
        contexts = env["project.agile.solution.context.revision"]
        for kind, values in (
            (
                "question",
                {
                    "question": "PRIVATE_QUESTION",
                    "owner_id": self.manager.id,
                    "planning_significance": "informational",
                },
            ),
            (
                "decision",
                {
                    "decision_context": "PRIVATE_DECISION",
                    "choice": "PRIVATE_CHOICE",
                    "consequences": "PRIVATE_CONSEQUENCES",
                },
            ),
        ):
            identity = env["project.agile.solution.context"].create(
                {
                    "name": "PRIVATE_CONTEXT",
                    "kind": kind,
                    "solution_id": self._thread().solution_id.id,
                }
            )
            contexts |= contexts.create(
                {
                    "context_id": identity.id,
                    "title": "PRIVATE_CONTEXT_TITLE",
                    "audience": "customer",
                    **values,
                }
            )
        document = env["project.agile.solution.document"].create(
            {
                "name": "PRIVATE_DOCUMENT",
                "kind": "spec",
                "solution_id": self._thread().solution_id.id,
                "approver_id": self.manager.id,
            }
        )
        baseline = env["project.agile.solution.revision"].create(
            {
                "document_id": document.id,
                "title": "PRIVATE_BASELINE",
                "requirement_revision_ids": [
                    Command.set(self.links[0].requirement_revision_id.ids)
                ],
                "context_revision_ids": [Command.set(contexts.ids)],
                "section_ids": [
                    Command.create(
                        {"title": "PRIVATE_SECTION", "body": "PRIVATE_NARRATIVE"}
                    )
                ],
            }
        )
        baseline.action_submit()
        baseline.action_approve()
        acceptance = env["project.agile.requirement.acceptance"].create(
            {
                "requirement_revision_id": self.links[0].requirement_revision_id.id,
                "document_revision_id": baseline.id,
                "decision": "accepted",
                "authority_label": "PRIVATE_AUTHORITY",
                "criteria_evaluated": "PRIVATE_CRITERIA",
                "evidence": "PRIVATE_ACCEPTANCE_EVIDENCE",
            }
        )
        snapshot = baseline.action_read_snapshot()["snapshot_json"]
        self._reply_as_analyst("Explicit BA reply")
        task = self.tasks[0].with_user(self.clients[0])
        cards = task.action_customer_requirements()
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["link_id"], self.links[0].id)
        self.assertEqual(cards[0]["requirement"]["title"], "Customer intent A")
        self.assertNotIn("PRIVATE_", json.dumps(cards))
        discussion = task.action_customer_requirement_discussion(self.links[0].id)
        self.assertIn("Explicit BA reply", str(discussion))
        self.assertNotIn("PRIVATE_", str(discussion))
        task.action_post_customer_requirement(self.links[0].id, "Discussion only")
        self.assertEqual(baseline.action_read_snapshot()["snapshot_json"], snapshot)
        self.assertEqual(acceptance.evidence, "PRIVATE_ACCEPTANCE_EVIDENCE")
        for source, field in (
            (contexts, "title"),
            (document, "name"),
            (baseline, "title"),
            (acceptance, "evidence"),
        ):
            with self.assertRaises(AccessError):
                source.with_user(self.clients[0]).read([field])
        self.assertEqual(
            env["project.agile.requirement.acceptance"].search([]), acceptance
        )
        for link in (self.links[1], self.private_links[0]):
            with self.assertRaises(AccessError):
                task.action_post_customer_requirement(link.id, "Not entitled")
            with self.assertRaises(AccessError):
                task.action_customer_requirement_discussion(link.id)

    def test_client_author_same_thread_successor_and_no_source_mutation(self):
        task = self.tasks[0].with_user(self.clients[0])
        revision = self.links[0].requirement_revision_id
        before = revision._snapshot_values()
        followers = self._thread().message_partner_ids
        task.with_context(
            default_author_id=self.clients[1].partner_id.id,
            default_model="project.task",
            default_res_id=self.tasks[1].id,
            default_subtype_id=self.env.ref("mail.mt_note").id,
            default_partner_ids=[Command.set(self.clients[1].partner_id.ids)],
            sudo=True,
            mail_post_autofollow=True,
        ).action_post_customer_requirement(
            self.links[0].id, "Client discussion <img src=x>"
        )
        message = self._shared_messages()
        self.assertEqual(len(message), 1)
        self.assertEqual(
            (message.model, message.res_id), (self._thread()._name, self._thread().id)
        )
        self.assertEqual(message.author_id, self.clients[0].partner_id)
        self.assertFalse(message.attachment_ids)
        self.assertEqual(self._thread().message_partner_ids, followers)
        self.assertEqual(revision._snapshot_values(), before)
        self.assertIn(
            "Client discussion",
            str(self._thread().with_user(self.analyst).message_ids.mapped("body")),
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [
                    ("mail_message_id", "=", message.id),
                    ("res_partner_id", "in", self.clients[1].partner_id.ids),
                ]
            )
        )
        self.assertFalse(
            self.env["project.agile.requirement.acceptance"].search(
                [
                    ("requirement_revision_id", "=", revision.id),
                ]
            )
        )
        self.links[0].action_refine_acceptance("Revised exact expectations")
        replacement = self.env["project.agile.requirement.task.link"].search(
            [
                ("task_id", "=", task.id),
                ("active", "=", True),
                ("requirement_revision_id.requirement_id", "=", self._thread().id),
            ]
        )
        self.assertEqual(replacement.requirement_revision_id.number, 2)
        self.assertIn(
            "Client discussion",
            str(task.action_customer_requirement_discussion(replacement.id)),
        )
        with self.assertRaises(AccessError):
            task.action_post_customer_requirement(self.links[0].id, "Retired edge")
        self._reply_as_analyst("Reply after revision")
        self.assertIn(
            "Reply after revision",
            str(task.action_customer_requirement_discussion(replacement.id)),
        )
        self.assertEqual(
            self._shared_messages().mapped("res_id"),
            [self._thread().id, self._thread().id],
        )
        self.assertEqual(revision._snapshot_values(), before)

    def test_two_clients_exact_contact_revocation_rules_and_company(self):
        # Native commercial-parent visibility succeeds; our exact-contact check
        # must still reject a sibling who has never been invited personally.
        self.assertTrue(self.tasks[0].with_user(self.sibling).read(["name"]))
        for user in (self.clients[1], self.sibling, self.outsider):
            with self.assertRaises(AccessError):
                self.tasks[0].with_user(user).action_customer_requirements()
        task = self.tasks[0].with_user(self.clients[0])
        self.assertTrue(task.action_customer_requirements())
        self.env["project.collaborator"].search(
            [
                ("project_id", "=", self.projects[0].id),
            ]
        ).unlink()
        self.projects[0].message_unsubscribe(partner_ids=self.clients[0].partner_id.ids)
        # Retained task follow/author privilege cannot replace Project sharing.
        with self.assertRaises(AccessError):
            task.action_post_customer_requirement(self.links[0].id, "Revoked")
        self.projects[0].message_subscribe(partner_ids=self.clients[0].partner_id.ids)
        self.assertTrue(task.action_customer_requirements())
        rule = self.env["ir.rule"].create(
            {
                "name": "Current customer Project restriction",
                "model_id": self.env.ref("project.model_project_project").id,
                "domain_force": repr([("id", "!=", self.projects[0].id)]),
            }
        )
        with self.assertRaises(AccessError):
            task.action_customer_requirements()
        rule.unlink()
        other = self.env["res.company"].create({"name": "Foreign customer company"})
        self.clients[0].company_ids = [Command.link(other.id)]
        with self.assertRaises(AccessError):
            task.with_context(
                allowed_company_ids=other.ids
            ).action_customer_requirements()
        self.assertTrue(task.action_customer_requirements())
        rule = self.env["ir.rule"].create(
            {
                "name": "Current internal requirement restriction",
                "model_id": self.env.ref(
                    "project_agile_solution.model_project_agile_requirement"
                ).id,
                "domain_force": repr([("id", "!=", self._thread().id)]),
            }
        )
        self.assertFalse(
            self.tasks[0].with_user(self.analyst).action_customer_requirements()
        )
        rule.unlink()

    def test_projection_does_not_grant_raw_source_mail_file_access(self):
        client = self.clients[0]
        self.tasks[0].with_user(client).action_post_customer_requirement(
            self.links[0].id, "Own visible message"
        )
        message = self._shared_messages()
        for source, field in (
            (self._thread(), "name"),
            (self.links[0], "requirement_revision_id"),
            (self.links[0].requirement_revision_id, "rationale"),
            (message, "body"),
        ):
            self._assert_payload_hidden(source, client, field)
            with self.assertRaises(AccessError):
                source.with_user(client).export_data([field])
        with self.assertRaises(AccessError):
            self._thread().with_user(client).message_post(body="Raw bypass")
        with self.assertRaises(AccessError):
            self._thread().with_user(client).message_subscribe(
                partner_ids=client.partner_id.ids
            )
        attachment, scheduled, pending = self._private_payloads(
            self._thread(), self.manager
        )
        for row, field in (
            (attachment, "datas"),
            (scheduled, "body"),
            (pending, "datas"),
        ):
            self._assert_payload_hidden(row, client, field)
        self.assertNotIn(
            "PRIVATE_",
            str(
                self.tasks[0]
                .with_user(client)
                .action_customer_requirement_discussion(self.links[0].id)
            ),
        )

    def test_bounded_complete_discussion_paging_and_typed_inputs(self):
        task = self.tasks[0].with_user(self.clients[0])
        for number in range(23):
            task.action_post_customer_requirement(
                self.links[0].id, f"Shared message {number}"
            )
        latest = task.action_customer_requirement_discussion(self.links[0].id)
        older = task.action_customer_requirement_discussion(
            self.links[0].id, latest["older_before"]
        )
        self.assertEqual(len(latest["messages"]), 20)
        self.assertEqual(len(older["messages"]), 3)
        self.assertFalse(older["older_before"])
        self.assertEqual(
            [row["text"] for row in older["messages"] + latest["messages"]],
            [f"Shared message {number}" for number in range(23)],
        )
        for invalid in (True, "1", -1):
            with self.assertRaises(ValidationError):
                task.action_post_customer_requirement(invalid, "Bad link")
        for body in ("", " " * 2, "x" * 10001):
            with self.assertRaises(ValidationError):
                task.action_post_customer_requirement(self.links[0].id, body)


@tagged("post_install", "-at_install")
class TestCustomerRequirementsHttp(CustomerRequirementFixture, HttpCase):
    _rpc = TestSolutionRenderTour._rpc
    _private_payloads = TestSolutionDiscussion._private_payloads

    def test_native_task_http_csrf_rpc_files_and_revocation(self):
        self.tasks[0]._portal_ensure_token()
        token_url = (
            f"/my/tasks/{self.tasks[0].id}?access_token={self.tasks[0].access_token}"
        )
        for user in (False, self.outsider, self.sibling):
            if user:
                self.authenticate(user.login, user.login)
            else:
                self.authenticate(None, None)
            token_page = self.url_open(token_url)
            self.assertEqual(token_page.status_code, 200)
            self.assertNotIn("Customer intent A", token_page.text)
            self.assertNotIn("solution_requirements", token_page.text)
        attachment, scheduled, pending = self._private_payloads(
            self._thread(), self.manager
        )
        tokens = {
            row.id: (row.generate_access_token()[0], row._get_raw_access_token())
            for row in attachment | pending
        }
        for index, client in enumerate(self.clients):
            self.authenticate(client.login, client.login)
            task, link = self.tasks[index], self.links[index]
            page = self.url_open(f"/my/tasks/{task.id}")
            self.assertEqual(page.status_code, 200)
            self.assertIn("Customer intent " + ("A" if index == 0 else "B"), page.text)
            self.assertNotIn("PRIVATE_", page.text)
            token = html.fromstring(page.content).xpath(
                '//input[@name="csrf_token"]/@value'
            )[0]
            url = f"/my/tasks/{task.id}/requirement-comment"
            for extra in (
                {},
                {"csrf_token": "wrong"},
                {"csrf_token": token, "author_id": self.clients[1 - index].id},
            ):
                self.assertEqual(
                    self.url_open(
                        url, data={"link_id": link.id, "body": "Forgery", **extra}
                    ).status_code,
                    400,
                )
            response = self.url_open(
                url,
                data={
                    "link_id": self.links[1 - index].id,
                    "body": "Foreign",
                    "csrf_token": token,
                },
            )
            self.assertEqual(response.status_code, 404)
            posted = self.url_open(
                url,
                data={
                    "link_id": link.id,
                    "body": "HTTP client post",
                    "csrf_token": token,
                },
            )
            self.assertEqual(posted.status_code, 200)
            self.assertIn("HTTP client post", posted.text)
            message = self._shared_messages(index)
            self.assertEqual(message.author_id, client.partner_id)
            projected = self._rpc(
                "project.task", "action_customer_requirements", [task.ids]
            )
            self.assertEqual(projected["result"][0]["link_id"], link.id)
            self.assertNotIn("PRIVATE_", str(projected["result"]))
            searched = self._rpc(
                "mail.message",
                "search_read",
                [[("id", "in", message.ids)], ["body"]],
            )
            self.assertFalse(searched.get("result"))
            raw_thread = self.url_open(
                "/mail/thread/messages",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "call",
                        "id": 1,
                        "params": {
                            "thread_model": self._thread(index)._name,
                            "thread_id": self._thread(index).id,
                        },
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            self.assertNotIn("HTTP client post", raw_thread.text)
            self.assertNotIn("PRIVATE_", raw_thread.text)
            for model, method, args in (
                (
                    "project.task",
                    "action_customer_requirements",
                    [self.tasks[1 - index].ids],
                ),
                (
                    "project.agile.requirement",
                    "read",
                    [self._thread(index).ids, ["name"]],
                ),
                ("mail.message", "read", [message.ids, ["body"]]),
                ("mail.scheduled.message", "read", [scheduled.ids, ["body"]]),
            ):
                denied = self._rpc(model, method, args, {"sudo": True})
                self.assertIn("error", denied)
                self.assertNotIn("PRIVATE_", str(denied))
            for row in attachment | pending:
                row.write({"public": True})
                self.env.flush_all()
                for access_token in ("", *tokens[row.id]):
                    denied = self.url_open(
                        f"/web/content/{row.id}?download=1&access_token={access_token}"
                    )
                    self.assertIn(denied.status_code, (403, 404))
                    self.assertNotIn(b"Private stable file payload", denied.content)
                    self.assertNotIn(b"Private scheduled file payload", denied.content)
            self.env["project.collaborator"].search(
                [("project_id", "=", self.projects[index].id)]
            ).unlink()
            self.projects[index].message_unsubscribe(partner_ids=client.partner_id.ids)
            self.env.flush_all()
            denied = self.url_open(
                url, data={"link_id": link.id, "body": "Revoked", "csrf_token": token}
            )
            self.assertEqual(denied.status_code, 404)
            self.assertEqual(len(self._shared_messages(index)), 1)

    def test_two_native_shared_story_browser_journeys(self):
        for index, client in enumerate(self.clients):
            self.start_tour(
                f"/my/projects/{self.projects[index].id}/project_sharing",
                "customer_requirement_discussion",
                login=client.login,
            )
            message = self._shared_messages(index)
            self.assertEqual(len(message), 1)
            self.assertEqual(message.author_id, client.partner_id)
            self.assertIn(
                "Browser customer question",
                str(
                    self._thread(index)
                    .with_user(self.analyst)
                    .message_ids.mapped("body")
                ),
            )

"""Exercise real mail exceptions and stable threads, not a mocked transport."""

import base64
import json
from datetime import timedelta
from email.message import EmailMessage
from uuid import uuid4

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import MockEmail, mail_new_test_user

from .test_solution_render_tour import TestSolutionRenderTour


class TestSolutionDiscussion(TransactionCase, MockEmail):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = mail_new_test_user(
            cls.env, "discussion_manager", groups="project.group_project_manager"
        )
        cls.reader = mail_new_test_user(
            cls.env,
            "discussion_reader",
            groups="project.group_project_user",
            notification_type="inbox",
        )
        cls.owner = mail_new_test_user(
            cls.env,
            "discussion_owner",
            groups="project.group_project_user",
            notification_type="inbox",
        )
        cls.portal = mail_new_test_user(
            cls.env, "discussion_portal", groups="base.group_portal"
        )
        cls.analyst = mail_new_test_user(
            cls.env,
            "discussion_analyst",
            groups="project_agile_solution.group_business_analyst",
        )
        cls.project = cls.env["project.project"].create(
            {
                "name": "Discussion Project",
                "agile_enabled": True,
                "agile_key": "DISCUSS",
                "privacy_visibility": "employees",
                "company_id": cls.env.company.id,
            }
        )
        cls.solution = (
            cls.env["project.agile.solution"]
            .with_user(cls.manager)
            .create(
                {
                    "name": "Discussion Solution",
                    "project_id": cls.project.id,
                }
            )
        )
        cls.requirement = (
            cls.env["project.agile.requirement"]
            .with_user(cls.manager)
            .create(
                {
                    "name": "Durable requirement",
                    "solution_id": cls.solution.id,
                }
            )
        )
        cls.context = (
            cls.env["project.agile.solution.context"]
            .with_user(cls.manager)
            .create(
                {
                    "name": "Durable question",
                    "kind": "question",
                    "solution_id": cls.solution.id,
                }
            )
        )
        cls.document = (
            cls.env["project.agile.solution.document"]
            .with_user(cls.manager)
            .create(
                {
                    "name": "Durable document",
                    "solution_id": cls.solution.id,
                    "approver_id": cls.manager.id,
                }
            )
        )

    def test_attachment_mutations_require_current_source(self):
        self._private_project()
        self.project.message_subscribe(partner_ids=self.analyst.partner_id.ids)
        attachments = self.env["ir.attachment"].with_user(self.analyst)
        for identity in (self.requirement, self.document, self.context):
            with self.subTest(model=identity._name):
                values = {
                    "name": "BA attachment",
                    "raw": b"Original mutation payload",
                    "res_model": identity._name,
                    "res_id": identity.id,
                }
                attachment = attachments.create(dict(values))
                attachment.write({"name": "Authorized edit"})
                self.assertEqual(attachment.name, "Authorized edit")
                self.assertEqual(attachment.create_uid, self.analyst)
                self.project.message_unsubscribe(
                    partner_ids=self.analyst.partner_id.ids
                )
                self.assertFalse(
                    identity.with_user(self.analyst).search([("id", "=", identity.id)])
                )
                with self.subTest(operation="create"):
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        attachments.create(dict(values))
                with self.subTest(operation="write"):
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        attachment.write({"name": "Forbidden edit"})
                with self.subTest(operation="unlink"):
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        attachment.unlink()
                self.assertTrue(attachment.sudo().exists())
                self.assertEqual(attachment.sudo().name, "Authorized edit")
                self.project.message_subscribe(partner_ids=self.analyst.partner_id.ids)
                attachment.write({"name": "Restored edit"})
                self.assertEqual(attachment.name, "Restored edit")
                attachment.unlink()
                self.assertFalse(attachment.exists())

    def test_scheduled_mutations_require_current_source(self):
        self._private_project()
        self.project.message_subscribe(partner_ids=self.analyst.partner_id.ids)
        messages = self.env["mail.scheduled.message"].with_user(self.analyst)
        for identity in (self.requirement, self.document, self.context):
            with self.subTest(model=identity._name):
                values = {
                    "model": identity._name,
                    "res_id": identity.id,
                    "author_id": self.analyst.partner_id.id,
                    "body": "Original scheduled payload",
                    "scheduled_date": fields.Datetime.now() + timedelta(days=1),
                }
                scheduled = messages.create(dict(values))
                scheduled.write({"body": "Authorized edit"})
                self.assertIn("Authorized edit", scheduled.body)
                self.assertEqual(scheduled.create_uid, self.analyst)
                self.project.message_unsubscribe(
                    partner_ids=self.analyst.partner_id.ids
                )
                self.assertFalse(
                    identity.with_user(self.analyst).search([("id", "=", identity.id)])
                )
                with self.subTest(operation="create"):
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        messages.create(dict(values))
                with self.subTest(operation="write"):
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        scheduled.write({"body": "Forbidden edit"})
                with self.subTest(operation="unlink"):
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        scheduled.unlink()
                self.assertTrue(scheduled.sudo().exists())
                self.assertIn("Authorized edit", scheduled.sudo().body)
                self.project.message_subscribe(partner_ids=self.analyst.partner_id.ids)
                scheduled.write({"body": "Restored edit"})
                self.assertIn("Restored edit", scheduled.body)
                scheduled.unlink()
                self.assertFalse(scheduled.exists())

    def test_attachment_relocation_checks_effective_destination(self):
        self._private_project()
        self.assertFalse(self.analyst.has_group("project.group_project_manager"))
        project = self.env["project.project"].create(
            {
                "name": "Visible attachment destination",
                "agile_enabled": True,
                "agile_key": "FILEOPEN",
                "privacy_visibility": "employees",
            }
        )
        solution = (
            self.env["project.agile.solution"]
            .with_user(self.manager)
            .create({"name": "Visible source", "project_id": project.id})
        )
        attachments = self.env["ir.attachment"].with_user(self.analyst)
        for identity in (self.requirement, self.document, self.context):
            with self.subTest(model=identity._name):
                self.assertFalse(
                    identity.with_user(self.analyst).search([("id", "=", identity.id)])
                )
                values = {"name": "Visible identity", "solution_id": solution.id}
                if identity == self.document:
                    values["approver_id"] = self.manager.id
                visible = (
                    self.env[identity._name].with_user(self.manager).create(values)
                )
                files = attachments.create(
                    [
                        {"name": name, "raw": b"Own writable payload"}
                        for name in ("first.txt", "second.txt")
                    ]
                )
                self.assertEqual(files.mapped("create_uid"), self.analyst)
                files.write({"name": "Still writable"})
                with self.assertRaises(AccessError), self.cr.savepoint():
                    files.write({"res_model": identity._name, "res_id": identity.id})
                self.assertEqual(files.sudo().mapped("res_model"), [False, False])
                files.write({"res_model": visible._name, "res_id": visible.id})
                with self.assertRaises(AccessError), self.cr.savepoint():
                    files.write({"res_id": identity.id})
                self.assertEqual(files.mapped("res_id"), [visible.id, visible.id])
                files.write({"res_model": False, "res_id": 0})
                files.write({"res_id": identity.id})
                with self.assertRaises(AccessError), self.cr.savepoint():
                    files.write({"res_model": identity._name})
                self.assertEqual(files.sudo().mapped("res_model"), [False, False])
                # The first effective destination is allowed; the second is not.
                files[0].write({"res_id": visible.id})
                with self.assertRaises(AccessError), self.cr.savepoint():
                    files.write({"res_model": identity._name})
                self.assertEqual(files.sudo().mapped("res_model"), [False, False])
                self.assertEqual(files.mapped("res_id"), [visible.id, identity.id])
                files.write({"res_model": visible._name, "res_id": visible.id})
                self.assertEqual(
                    files.mapped("res_model"), [visible._name, visible._name]
                )
                files.unlink()
                self.assertFalse(files.exists())

    def _incoming_reply(self, parent_message_id, sender, body="Native incoming reply"):
        # Freeze the legitimate reference before revoking the original author.
        message = EmailMessage()
        message["From"] = sender
        message["To"] = "discussion@example.test"
        message["Subject"] = "Re: stable Solution discussion"
        message["Message-ID"] = f"<{uuid4()}@example.test>"
        message["In-Reply-To"] = parent_message_id
        message["References"] = parent_message_id
        message.set_content(body)
        message.add_attachment(
            b"Native reply file", maintype="text", subtype="plain", filename="reply.txt"
        )
        return message

    def test_native_gateway_replies_use_current_author_and_original_thread(self):
        self._private_project()
        self.reader.email = "discussion.reader@example.test"
        self.owner.email = "discussion.outsider@example.test"
        for identity in (self.requirement, self.document, self.context):
            with self.subTest(model=identity._name):
                self.project.message_subscribe(partner_ids=self.reader.partner_id.ids)
                parent_message_id = self._post(identity).message_id
                incoming = self._incoming_reply(
                    parent_message_id, self.reader.email_formatted
                )
                with self.mock_mail_gateway():
                    result = self.env["mail.thread"].message_process(
                        None, incoming.as_bytes()
                    )
                self.assertEqual(result, identity.id)
                reply = self.env["mail.message"].search(
                    [("message_id", "=", incoming["Message-ID"])]
                )
                self.assertEqual(len(reply), 1)
                self.assertEqual(
                    (reply.model, reply.res_id), (identity._name, identity.id)
                )
                self.assertEqual(reply.author_id, self.reader.partner_id)
                self.assertEqual(reply.create_uid, self.env.ref("base.user_root"))
                self.assertEqual(reply.message_type, "email")
                self.assertIn(
                    "Native incoming reply", reply.with_user(self.reader).body
                )
                self.assertEqual(reply.attachment_ids.name, "reply.txt")
                self.assertEqual(reply.attachment_ids.raw, b"Native reply file")
                with self.mock_mail_gateway():
                    self.assertFalse(
                        self.env["mail.thread"].message_process(
                            None, incoming.as_bytes()
                        )
                    )
                self.assertEqual(
                    self.env["mail.message"].search_count(
                        [("message_id", "=", incoming["Message-ID"])]
                    ),
                    1,
                )
                # Authorship/following does not survive native Project revocation.
                self.project.message_unsubscribe(partner_ids=self.reader.partner_id.ids)
                self.assertFalse(
                    identity.with_user(self.reader).search([("id", "=", identity.id)])
                )
                before = identity.message_ids
                for sender in (
                    self.reader.email_formatted,
                    self.owner.email_formatted,
                    self.portal.email_formatted,
                    "Unknown <unbound@example.test>",
                ):
                    rejected = self._incoming_reply(
                        parent_message_id, sender, "Rejected reply"
                    )
                    with (
                        self.mock_mail_gateway(),
                        self.assertRaises(AccessError),
                        self.cr.savepoint(),
                    ):
                        self.env["mail.thread"].message_process(
                            None, rejected.as_bytes()
                        )
                    self.assertFalse(
                        self.env["mail.message"].search(
                            [("message_id", "=", rejected["Message-ID"])]
                        )
                    )
                self.assertEqual(identity.message_ids, before)
                self._assert_payload_hidden(reply, self.reader, "body")
                self._assert_payload_hidden(reply.attachment_ids, self.reader, "datas")
                self.assertFalse(
                    self.env["mail.notification"].search(
                        [
                            ("mail_message_id", "=", reply.id),
                            (
                                "res_partner_id",
                                "in",
                                (self.owner | self.portal).partner_id.ids,
                            ),
                        ]
                    )
                )

    def test_gateway_rechecks_custom_rules_company_and_active_author(self):
        self.reader.email = "discussion.reader.rules@example.test"
        parent_message_id = self._post(self.requirement).message_id
        gateway = self.env["mail.thread"]
        rule = self.env["ir.rule"].create(
            {
                "name": "Current gateway source rule",
                "model_id": self.env["ir.model"]._get_id(self.requirement._name),
                "domain_force": repr([("id", "!=", self.requirement.id)]),
            }
        )
        incoming = self._incoming_reply(parent_message_id, self.reader.email_formatted)
        with (
            self.mock_mail_gateway(),
            self.assertRaises(AccessError),
            self.cr.savepoint(),
        ):
            gateway.message_process(None, incoming.as_bytes())
        rule.unlink()
        other = self.env["res.company"].create({"name": "Gateway other company"})
        original_company = self.reader.company_id
        self.reader.write(
            {"company_ids": [Command.set(other.ids)], "company_id": other.id}
        )
        incoming = self._incoming_reply(parent_message_id, self.reader.email_formatted)
        with (
            self.mock_mail_gateway(),
            self.assertRaises(AccessError),
            self.cr.savepoint(),
        ):
            gateway.message_process(None, incoming.as_bytes())
        self.reader.write(
            {
                "company_ids": [Command.set(original_company.ids)],
                "company_id": original_company.id,
                "active": False,
            }
        )
        incoming = self._incoming_reply(parent_message_id, self.reader.email_formatted)
        with (
            self.mock_mail_gateway(),
            self.assertRaises(AccessError),
            self.cr.savepoint(),
        ):
            gateway.message_process(None, incoming.as_bytes())
        self.reader.active = True
        with self.mock_mail_gateway():
            self.assertEqual(
                gateway.message_process(None, incoming.as_bytes()), self.requirement.id
            )
        self.assertEqual(
            self.env["mail.message"]
            .search(
                [
                    ("message_id", "=", incoming["Message-ID"]),
                ]
            )
            .author_id,
            self.reader.partner_id,
        )

    def test_gateway_authority_cannot_be_forged_by_public_methods_or_context(self):
        self._private_project()
        self.reader.email = "discussion.reader.spoof@example.test"
        for identity in (self.requirement, self.document, self.context):
            parent_message_id = self._post(identity).message_id
            incoming = self._incoming_reply(
                parent_message_id, self.reader.email_formatted
            )
            caller = identity.with_user(self.owner).with_context(
                sudo=True,
                _solution_gateway_reply={
                    "author_id": self.reader.partner_id.id,
                    "user_id": self.reader.id,
                    "targets": [[identity._name, identity.id]],
                },
                default_author_id=self.reader.partner_id.id,
            )
            before = identity.message_ids
            with self.assertRaises(AccessError), self.cr.savepoint():
                caller.message_post(
                    author_id=self.reader.partner_id.id,
                    email_from=self.reader.email_formatted,
                    message_type="email",
                    body="Spoofed direct post",
                )
            with (
                self.mock_mail_gateway(),
                self.assertRaisesRegex(
                    AccessError, "Administrative mail gateway access is required"
                ),
                self.cr.savepoint(),
            ):
                caller.env["mail.thread"].message_process(None, incoming.as_bytes())
            with self.assertRaises(AccessError), self.cr.savepoint():
                identity.with_user(self.env.ref("base.user_root")).message_post(
                    author_id=self.reader.partner_id.id,
                    email_from=self.reader.email_formatted,
                    body="No blanket OdooBot authority",
                )
            # Public message_update receives no private provenance either.
            caller.message_update({"author_id": self.reader.partner_id.id})
            self.assertEqual(identity.message_ids, before)

    def test_revoked_self_unfollow_only_removes_own_subscription(self):
        self._private_project()
        other = self.env["res.company"].create({"name": "Unfollow company"})
        self.reader.company_ids = [Command.link(other.id)]
        for identity in (self.requirement, self.document, self.context):
            self.project.message_subscribe(partner_ids=self.reader.partner_id.ids)
            self._post(identity)
            identity.message_subscribe(
                partner_ids=(self.manager | self.owner).partner_id.ids
            )
            follower = self.env["mail.followers"].search(
                [
                    ("res_model", "=", identity._name),
                    ("res_id", "=", identity.id),
                    ("partner_id", "=", self.reader.partner_id.id),
                ]
            )
            self.assertTrue(follower)
            others = identity.message_follower_ids - follower
            others_before = others.read(["partner_id", "subtype_ids"])
            message = identity.message_ids[0]
            attachment, scheduled, pending = self._private_payloads(
                identity, self.reader
            )
            messages_before = identity.message_ids.read(
                ["body", "author_id", "attachment_ids"]
            )
            # Observe unchanged files independently of the revoked reader below.
            files = (attachment | pending).with_env(self.env)
            files_before = files.read(["datas", "res_model", "res_id"])
            notifications = self.env["mail.notification"].search(
                [
                    ("mail_message_id", "in", identity.message_ids.ids),
                ]
            )
            notifications_before = notifications.read(
                ["res_partner_id", "is_read", "notification_status"]
            )
            self.project.message_unsubscribe(partner_ids=self.reader.partner_id.ids)
            caller = identity.with_user(self.reader).with_context(
                allowed_company_ids=other.ids, active_test=False, sudo=True
            )
            self.assertFalse(caller.search([("id", "=", identity.id)]))
            with self.assertRaises(AccessError), self.cr.savepoint():
                caller.message_unsubscribe((self.reader | self.manager).partner_id.ids)
            self.assertTrue(follower.exists())
            with self.assertRaises(AccessError), self.cr.savepoint():
                caller.message_unsubscribe(self.manager.partner_id.ids)
            self.assertIsNone(caller.message_unsubscribe(self.reader.partner_id.ids))
            self.assertFalse(follower.exists())
            self.assertIsNone(caller.message_unsubscribe(self.reader.partner_id.ids))
            self.assertEqual(identity.message_follower_ids, others)
            self.assertEqual(others.read(["partner_id", "subtype_ids"]), others_before)
            self.assertEqual(
                identity.message_ids.read(["body", "author_id", "attachment_ids"]),
                messages_before,
            )
            self.assertEqual(
                files.read(["datas", "res_model", "res_id"]),
                files_before,
            )
            self.assertEqual(
                notifications.read(
                    ["res_partner_id", "is_read", "notification_status"]
                ),
                notifications_before,
            )
            for row, field in (
                (identity, "name"),
                (message, "body"),
                (attachment, "datas"),
                (pending, "datas"),
                (scheduled, "body"),
            ):
                self._assert_payload_hidden(row, self.reader, field)
            with self.assertRaises(AccessError):
                caller.message_post(body="Unfollow is not access")
            fresh = identity.with_context(mail_notify_force_send=False).message_post(
                body="After self-unfollow",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                partner_ids=self.reader.partner_id.ids,
            )
            self.assertFalse(
                self.env["mail.notification"].search(
                    [
                        ("mail_message_id", "=", fresh.id),
                        ("res_partner_id", "=", self.reader.partner_id.id),
                    ]
                )
            )

    def test_question_owner_without_source_access_is_not_automatically_followed(self):
        self._private_project()
        self.assertFalse(
            self.context.with_user(self.owner).search([("id", "=", self.context.id)])
        )
        question = self._question()
        self.assertNotIn(self.owner.partner_id, self.context.message_partner_ids)
        # Manual/previous followers are retained, including their own subtypes.
        self.context.message_subscribe(partner_ids=self.owner.partner_id.ids)
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", self.context._name),
                ("res_id", "=", self.context.id),
                ("partner_id", "=", self.owner.partner_id.id),
            ]
        )
        note = self.env.ref("mail.mt_note")
        follower.write({"subtype_ids": [Command.set(note.ids)]})
        question.write({"owner_id": self.reader.id})
        question.write({"owner_id": self.owner.id})
        self.assertEqual(follower.subtype_ids, note)
        self.assertIn(self.reader.partner_id, self.context.message_partner_ids)
        question.write({"owner_id": self.analyst.id})
        self.assertNotIn(self.analyst.partner_id, self.context.message_partner_ids)
        self.project.message_subscribe(partner_ids=self.analyst.partner_id.ids)
        # Membership changes alone do not subscribe; assignment is the trigger.
        self.assertNotIn(self.analyst.partner_id, self.context.message_partner_ids)
        question.write({"owner_id": self.analyst.id})
        self.assertIn(self.analyst.partner_id, self.context.message_partner_ids)
        self.assertEqual(follower.subtype_ids, note)
        message = self._post(self.context, partner_ids=self.owner.partner_id.ids)
        self.assertFalse(
            self.env["mail.notification"].search(
                [
                    ("mail_message_id", "=", message.id),
                    ("res_partner_id", "=", self.owner.partner_id.id),
                ]
            )
        )
        with self.assertRaises(AccessError):
            self.context.with_user(self.owner).read(["name"])

    def _post(self, record, **values):
        return (
            record.with_user(self.reader)
            .with_context(mail_notify_force_send=False)
            .message_post(
                body="Persistent discussion",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                **values,
            )
        )

    def _question(self):
        return (
            self.env["project.agile.solution.context.revision"]
            .with_user(self.manager)
            .create(
                {
                    "context_id": self.context.id,
                    "title": "Owned question",
                    "question": "Who decides?",
                    "planning_significance": "planning",
                    "owner_id": self.owner.id,
                }
            )
        )

    def _private_payloads(self, identity, author):
        caller = identity.with_user(author).with_context(mail_notify_force_send=False)
        message = caller.message_post(
            body="Private attachment discussion",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            attachments=[("discussion.txt", b"Private stable file payload")],
        )
        attachment = caller.env["ir.attachment"].create(
            {
                "name": "scheduled.txt",
                "raw": b"Private scheduled file payload",
                "res_model": "mail.compose.message",
                "res_id": 0,
            }
        )
        scheduled = caller.env["mail.scheduled.message"].create(
            {
                "model": identity._name,
                "res_id": identity.id,
                "author_id": author.partner_id.id,
                "body": "Private scheduled discussion",
                "scheduled_date": fields.Datetime.now() + timedelta(days=1),
                "attachment_ids": [Command.link(attachment.id)],
            }
        )
        self.assertEqual(
            (attachment.res_model, attachment.res_id), (scheduled._name, scheduled.id)
        )
        return message.attachment_ids, scheduled, attachment

    def _assert_payload_hidden(self, record, user, field, **context):
        caller = record.with_user(user).with_context(
            sudo=True, active_test=False, **context
        )
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            caller.read([field])
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            _content = caller[field]
        domain = [("id", "=", record.id)]
        # Nightlies may reject the model ACL or filter out inaccessible rows.
        try:
            records = caller.search(domain)
        except AccessError:
            records = None
        self.assertFalse(records)
        try:
            rows = caller.search_read(domain, [field])
        except AccessError:
            rows = None
        self.assertFalse(rows)

    def _private_project(self):
        self.project.message_subscribe(
            partner_ids=(self.manager | self.reader).partner_id.ids
        )
        self.project.write({"privacy_visibility": "followers"})

    def test_chatter_attachments_current_source_authority(self):
        self._private_project()
        for identity in (self.requirement, self.document, self.context):
            with self.subTest(model=identity._name):
                attachment, _scheduled, pending = self._private_payloads(
                    identity, self.reader
                )
                for file, payload in (
                    (attachment, b"Private stable file payload"),
                    (pending, b"Private scheduled file payload"),
                ):
                    self.assertEqual(
                        base64.b64decode(
                            file.with_user(self.reader).read(["datas"])[0]["datas"]
                        ),
                        payload,
                    )
                    self.assertTrue(
                        file.with_user(self.reader).search([("id", "=", file.id)])
                    )
                    self.assertFalse(
                        identity.with_user(self.owner).search(
                            [("id", "=", identity.id)]
                        )
                    )
                    self._assert_payload_hidden(file, self.owner, "datas")
                    self._assert_payload_hidden(file, self.portal, "datas")
                self.project.message_unsubscribe(partner_ids=self.reader.partner_id.ids)
                self.assertFalse(
                    identity.with_user(self.reader).search([("id", "=", identity.id)])
                )
                for file in attachment | pending:
                    self._assert_payload_hidden(file, self.reader, "datas")
                    file.sudo().write({"public": True})
                    self._assert_payload_hidden(file, self.reader, "datas")
                self.project.message_subscribe(partner_ids=self.reader.partner_id.ids)
                self.assertEqual(
                    base64.b64decode(
                        attachment.with_user(self.reader).read(["datas"])[0]["datas"]
                    ),
                    b"Private stable file payload",
                )

    def test_scheduled_messages_current_source_authority(self):
        self._private_project()
        for identity in (self.requirement, self.document, self.context):
            with self.subTest(model=identity._name):
                _attachment, scheduled, _pending = self._private_payloads(
                    identity, self.reader
                )
                self.assertIn(
                    "Private scheduled discussion",
                    scheduled.with_user(self.reader).body,
                )
                self.assertTrue(
                    scheduled.with_user(self.reader).search_read(
                        [("id", "=", scheduled.id)], ["body"]
                    )
                )
                for user in (self.owner, self.portal):
                    self._assert_payload_hidden(scheduled, user, "body")
                self.project.message_unsubscribe(partner_ids=self.reader.partner_id.ids)
                self.assertFalse(
                    identity.with_user(self.reader).search([("id", "=", identity.id)])
                )
                self._assert_payload_hidden(scheduled, self.reader, "body")
                self.project.message_subscribe(partner_ids=self.reader.partner_id.ids)
                self.assertIn(
                    "Private scheduled discussion",
                    scheduled.with_user(self.reader).read(["body"])[0]["body"],
                )

    def test_payloads_follow_current_company_and_custom_source_rules(self):
        other = self.env["res.company"].create({"name": "Other file company"})
        self.reader.company_ids = [Command.link(other.id)]
        for identity in (self.requirement, self.document, self.context):
            attachment, scheduled, pending = self._private_payloads(
                identity, self.reader
            )
            for row, field in (
                (attachment, "datas"),
                (pending, "datas"),
                (scheduled, "body"),
            ):
                self._assert_payload_hidden(
                    row, self.reader, field, allowed_company_ids=other.ids
                )
            rule = self.env["ir.rule"].create(
                {
                    "name": "Current custom source restriction",
                    "model_id": self.env["ir.model"]._get_id(identity._name),
                    "domain_force": repr([("id", "!=", identity.id)]),
                }
            )
            for row, field in (
                (attachment, "datas"),
                (pending, "datas"),
                (scheduled, "body"),
            ):
                self._assert_payload_hidden(row, self.reader, field)
            rule.unlink()
            self.assertTrue(
                attachment.with_user(self.reader).read(["datas"])[0]["datas"]
            )
            self.assertIn(
                "Private scheduled discussion",
                scheduled.with_user(self.reader).read(["body"])[0]["body"],
            )

    def test_unrelated_task_payloads_keep_native_access(self):
        task = (
            self.env["project.task"]
            .with_user(self.manager)
            .create({"name": "Native files", "project_id": self.project.id})
        )
        attachment, scheduled, pending = self._private_payloads(task, self.manager)
        for row in attachment | pending:
            row.with_user(self.manager).write({"name": "Native attachment edit"})
            self.assertTrue(row.with_user(self.reader).search([("id", "=", row.id)]))
            self.assertTrue(row.with_user(self.reader).read(["datas"])[0]["datas"])
        self.assertIn(
            "Private scheduled discussion",
            scheduled.with_user(self.reader).read(["body"])[0]["body"],
        )
        self.assertTrue(
            scheduled.with_user(self.reader).search([("id", "=", scheduled.id)])
        )
        scheduled.with_user(self.manager).write({"subject": "Native scheduled edit"})
        self.assertEqual(
            scheduled.with_user(self.manager).subject, "Native scheduled edit"
        )
        (attachment | pending).with_user(self.manager).unlink()
        scheduled.with_user(self.manager).unlink()
        self.assertFalse((attachment | pending).exists())
        self.assertFalse(scheduled.exists())

    def test_threads_survive_successors_without_changing_frozen_content(self):
        requirement = (
            self.env["project.agile.requirement.revision"]
            .with_user(self.manager)
            .create(
                {
                    "requirement_id": self.requirement.id,
                    "title": "First intent",
                    "description": "Original scope",
                    "rationale": "Keep scope",
                    "verification_method": "Read original scope",
                    "acceptance_expectations": "Unchanged",
                }
            )
        )
        question = self._question()
        revision = (
            self.env["project.agile.solution.revision"]
            .with_user(self.manager)
            .create(
                {
                    "document_id": self.document.id,
                    "title": "First baseline",
                    "section_ids": [
                        Command.create(
                            {"title": "Scope", "body": "<p>Agreed scope</p>"}
                        )
                    ],
                    "requirement_revision_ids": [Command.set(requirement.ids)],
                    "context_revision_ids": [Command.set(question.ids)],
                }
            )
        )
        revision.action_submit()
        revision.action_approve()
        before = revision.action_read_snapshot()["snapshot_json"]
        content = (requirement._snapshot_values(), question._snapshot_values())
        for identity in (self.requirement, self.document, self.context):
            message = self._post(identity)
            identity.action_new_revision()
            self.assertIn(message, identity.with_user(self.reader).message_ids)
            self.assertEqual(
                (message.model, message.res_id), (identity._name, identity.id)
            )
        self.assertEqual(revision.action_read_snapshot()["snapshot_json"], before)
        self.assertEqual(
            (requirement._snapshot_values(), question._snapshot_values()), content
        )
        self.assertTrue(requirement.sealed and question.sealed)

    def test_owner_following_preserves_manual_subtypes_and_native_mentions(self):
        question = self._question()
        self.assertIn(self.owner.partner_id, self.context.message_partner_ids)
        self.context.message_subscribe(partner_ids=self.reader.partner_id.ids)
        follower = self.env["mail.followers"].search(
            [
                ("res_model", "=", self.context._name),
                ("res_id", "=", self.context.id),
                ("partner_id", "=", self.owner.partner_id.id),
            ]
        )
        note = self.env.ref("mail.mt_note")
        follower.write({"subtype_ids": [Command.set(note.ids)]})
        question.write({"owner_id": self.reader.id})
        question.write({"owner_id": self.owner.id})
        self.assertEqual(follower.subtype_ids, note)
        self.assertIn(self.reader.partner_id, self.context.message_partner_ids)
        message = self._post(self.context, partner_ids=self.owner.partner_id.ids)
        notification = self.env["mail.notification"].search(
            [
                ("mail_message_id", "=", message.id),
                ("res_partner_id", "=", self.owner.partner_id.id),
            ]
        )
        self.assertEqual(notification.notification_type, "inbox")
        self.assertIn("Persistent discussion", message.with_user(self.owner).body)
        self.context.with_user(self.reader).message_unsubscribe(
            self.reader.partner_id.ids
        )
        self.assertNotIn(self.reader.partner_id, self.context.message_partner_ids)

    def test_revocation_blocks_author_recipient_and_follower_exceptions(self):
        for identity in (self.requirement, self.document, self.context):
            message = self._post(identity, partner_ids=self.owner.partner_id.ids)
            follower = self.env["mail.followers"].search(
                [
                    ("res_model", "=", identity._name),
                    ("res_id", "=", identity.id),
                    ("partner_id", "=", self.reader.partner_id.id),
                ]
            )
            self.assertTrue(follower)
            rule = self.env["ir.rule"].create(
                {
                    "name": "Revoke concrete source",
                    "model_id": self.env["ir.model"]._get_id(identity._name),
                    "domain_force": repr([("id", "!=", identity.id)]),
                }
            )
            for user in (self.reader, self.owner, self.portal):
                with self.subTest(model=identity._name, user=user.login):
                    caller = identity.with_user(user)
                    with self.assertRaises(AccessError):
                        caller.read(["name"])
                    with self.assertRaises(AccessError):
                        self.env["mail.message"].with_user(user).browse(
                            message.id
                        ).read(["body"])
                    self.env.invalidate_all()
                    with self.assertRaises(AccessError):
                        _body = (
                            self.env["mail.message"]
                            .with_user(user)
                            .browse(message.id)
                            .body
                        )
                    self.assertFalse(
                        self.env["mail.message"]
                        .with_user(user)
                        .search([("id", "=", message.id)])
                    )
                    fetched = (
                        self.env["mail.message"]
                        .with_user(user)
                        .sudo()
                        ._message_fetch([("id", "=", message.id)])
                    )
                    self.assertFalse(fetched["messages"])
                    with self.assertRaises(AccessError):
                        caller.message_post(body="Forbidden")
                    with self.assertRaises(AccessError):
                        caller.message_subscribe(partner_ids=user.partner_id.ids)
                    with self.assertRaises(AccessError):
                        caller.message_unsubscribe(
                            partner_ids=self.manager.partner_id.ids
                        )
                    with self.assertRaises(AccessError):
                        follower.with_user(user).read(["partner_id"])
                    if user.share:
                        with self.assertRaises(AccessError):
                            follower.with_user(user).search(
                                [("id", "in", follower.ids)]
                            )
                    else:
                        self.assertFalse(
                            follower.with_user(user).search(
                                [("id", "in", follower.ids)]
                            )
                        )
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        follower.with_user(user).write(
                            {"subtype_ids": [Command.clear()]}
                        )
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        follower.with_user(user).unlink()
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        message.with_user(user).write({"body": "Forbidden edit"})
                    with self.assertRaises(AccessError), self.cr.savepoint():
                        self.env["mail.message"].with_user(user).create(
                            {
                                "model": identity._name,
                                "res_id": identity.id,
                                "body": "Follower bypass",
                                "parent_id": message.id,
                            }
                        )
            rule.unlink()
            self.assertIn(
                "Persistent discussion",
                message.with_user(self.reader).read(["body"])[0]["body"],
            )

    def test_current_project_company_access_and_recipient_filtering(self):
        self._question()
        # Existing follows/mentions do not retain revoked native Project access.
        self.context.message_subscribe(partner_ids=self.reader.partner_id.ids)
        self.project.write({"privacy_visibility": "followers"})
        with self.assertRaises(AccessError):
            self.project.with_user(self.owner).read(["name"])
        with self.assertRaises(AccessError):
            self.context.with_user(self.owner).read(["name"])
        self.project.message_subscribe(partner_ids=self.manager.partner_id.ids)
        message = (
            self.context.with_user(self.manager)
            .with_context(mail_notify_force_send=False)
            .message_post(
                body="Private Project",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                partner_ids=(
                    self.owner.partner_id
                    | self.reader.partner_id
                    | self.portal.partner_id
                ).ids,
                outgoing_email_to="outsider@example.invalid",
            )
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [
                    ("mail_message_id", "=", message.id),
                    (
                        "res_partner_id",
                        "in",
                        (
                            self.owner.partner_id
                            | self.reader.partner_id
                            | self.portal.partner_id
                        ).ids,
                    ),
                ]
            )
        )
        self.assertFalse(
            self.env["mail.mail"].search([("mail_message_id", "=", message.id)])
        )
        for user in (self.reader, self.owner):
            with self.assertRaises(AccessError):
                message.with_user(user).read(["body"])
        self.project.message_subscribe(partner_ids=self.owner.partner_id.ids)
        allowed = (
            self.context.with_user(self.manager)
            .with_context(mail_notify_force_send=False)
            .message_post(
                body="Allowed owner",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                partner_ids=self.owner.partner_id.ids,
            )
        )
        self.assertTrue(
            self.env["mail.notification"].search(
                [
                    ("mail_message_id", "=", allowed.id),
                    ("res_partner_id", "=", self.owner.partner_id.id),
                ]
            )
        )
        other = self.env["res.company"].create({"name": "Foreign discussion company"})
        self.manager.company_ids = [Command.link(other.id)]
        project = self.env["project.project"].create(
            {
                "name": "Foreign discussion",
                "agile_enabled": True,
                "agile_key": "FDISCUSS",
                "company_id": other.id,
                "privacy_visibility": "employees",
            }
        )
        caller = (
            self.env["project.agile.solution"]
            .with_user(self.manager)
            .with_context(
                allowed_company_ids=(self.env.company | other).ids,
            )
        )
        solution = caller.create({"name": "Foreign", "project_id": project.id})
        identity = caller.env["project.agile.requirement"].create(
            {"name": "Foreign", "solution_id": solution.id}
        )
        hidden_message = identity.with_context(
            mail_notify_force_send=False
        ).message_post(
            body="Company secret",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            partner_ids=self.reader.partner_id.ids,
        )
        with self.assertRaises(AccessError):
            hidden_message.with_user(self.reader).read(["body"])
        with self.assertRaises(AccessError):
            identity.with_user(self.reader).message_post(body="Company bypass")
        self.assertFalse(
            self.env["mail.notification"].search(
                [
                    ("mail_message_id", "=", hidden_message.id),
                    ("res_partner_id", "=", self.reader.partner_id.id),
                ]
            )
        )

    def test_unrelated_native_threads_keep_their_access_semantics(self):
        employee = mail_new_test_user(
            self.env, "discussion_plain_employee", groups="base.group_user"
        )
        own_message = (
            self.env["mail.message"]
            .with_user(employee)
            .create(
                {
                    "body": "Ordinary private discussion",
                    "message_type": "comment",
                }
            )
        )
        self.assertIn(
            "Ordinary private discussion", own_message.read(["body"])[0]["body"]
        )
        message = self.project.with_user(self.manager).message_post(
            body="Ordinary native Project"
        )
        self.assertIn(
            "Ordinary native Project",
            message.with_user(self.manager).read(["body"])[0]["body"],
        )


@tagged("post_install", "-at_install")
class TestSolutionDiscussionTour(HttpCase):
    _rpc = TestSolutionRenderTour._rpc

    _private_payloads = TestSolutionDiscussion._private_payloads

    def test_private_attachment_download_and_scheduled_rpc(self):
        manager = mail_new_test_user(
            self.env, "file_manager", groups="project.group_project_manager"
        )
        reader = mail_new_test_user(
            self.env, "file_reader", groups="project.group_project_user"
        )
        outsider = mail_new_test_user(
            self.env, "file_outsider", groups="project.group_project_user"
        )
        portal = mail_new_test_user(self.env, "file_portal", groups="base.group_portal")
        project = self.env["project.project"].create(
            {
                "name": "Private files",
                "agile_enabled": True,
                "agile_key": "FILEPRIV",
                "privacy_visibility": "followers",
            }
        )
        project.message_subscribe(partner_ids=(manager | reader).partner_id.ids)
        solution = (
            self.env["project.agile.solution"]
            .with_user(manager)
            .create({"name": "Private files", "project_id": project.id})
        )
        for model, extra in (
            ("project.agile.requirement", {}),
            ("project.agile.solution.document", {"approver_id": manager.id}),
            ("project.agile.solution.context", {"kind": "question"}),
        ):
            with self.subTest(model=model):
                project.message_subscribe(partner_ids=reader.partner_id.ids)
                identity = (
                    self.env[model]
                    .with_user(manager)
                    .create(
                        {"name": "Private source", "solution_id": solution.id, **extra}
                    )
                )
                attachment, scheduled, pending = self._private_payloads(
                    identity, reader
                )
                tokens = {
                    file.id: (
                        file.sudo().generate_access_token()[0],
                        file.sudo()._get_raw_access_token(),
                    )
                    for file in attachment | pending
                }
                self.env.flush_all()
                self.authenticate(reader.login, reader.login)
                for file, payload in (
                    (attachment, b"Private stable file payload"),
                    (pending, b"Private scheduled file payload"),
                ):
                    response = self.url_open(f"/web/content/{file.id}?download=1")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content, payload)
                self.assertIn(
                    "Private scheduled discussion",
                    str(
                        self._rpc(
                            "mail.scheduled.message", "read", [scheduled.ids, ["body"]]
                        )["result"]
                    ),
                )
                project.message_unsubscribe(partner_ids=reader.partner_id.ids)
                self.env.flush_all()
                for user in (outsider, reader, portal):
                    self.authenticate(user.login, user.login)
                    if not user.share:
                        self.assertFalse(
                            self._rpc(model, "search", [[("id", "=", identity.id)]])[
                                "result"
                            ]
                        )
                    for file in attachment | pending:
                        file.sudo().write({"public": True})
                        self.env.flush_all()
                        for token in ("", *tokens[file.id]):
                            response = self.url_open(
                                f"/web/content/{file.id}?download=1&access_token={token}"
                            )
                            self.assertIn(response.status_code, (403, 404))
                            self.assertNotIn(
                                b"Private stable file payload", response.content
                            )
                            self.assertNotIn(
                                b"Private scheduled file payload", response.content
                            )
                    denied = self._rpc(
                        "mail.scheduled.message", "read", [scheduled.ids, ["body"]]
                    )
                    self.assertEqual(
                        denied["error"]["data"]["name"], "odoo.exceptions.AccessError"
                    )
                    self.assertNotIn("Private scheduled discussion", str(denied))
                project.message_subscribe(partner_ids=reader.partner_id.ids)

        # Unrelated public attachments retain the native public/token transport.
        public = self.env["ir.attachment"].create(
            {"name": "public.txt", "raw": b"Ordinary public file", "public": True}
        )
        self.env.flush_all()
        response = self.url_open(f"/web/content/{public.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Ordinary public file")

    def test_native_stable_chatter_and_direct_rpc_access(self):
        manager = mail_new_test_user(
            self.env,
            "discussion_tour_manager",
            groups="project.group_project_manager",
        )
        reader = mail_new_test_user(
            self.env,
            "discussion_tour_reader",
            groups="project.group_project_user",
            notification_type="inbox",
        )
        project = self.env["project.project"].create(
            {
                "name": "Native discussions",
                "agile_enabled": True,
                "agile_key": "DISCUSSUI",
                "privacy_visibility": "employees",
            }
        )
        solution = (
            self.env["project.agile.solution"]
            .with_user(manager)
            .create(
                {
                    "name": "Native discussions",
                    "project_id": project.id,
                }
            )
        )
        for model, extra in (
            ("project.agile.requirement", {}),
            ("project.agile.solution.context", {"kind": "question"}),
            ("project.agile.solution.document", {"approver_id": manager.id}),
        ):
            identity = (
                self.env[model]
                .with_user(manager)
                .create(
                    {
                        "name": "Shared native discussion",
                        "solution_id": solution.id,
                        **extra,
                    }
                )
            )
            action = self.env["ir.actions.act_window"].create(
                {
                    "name": "Stable conversation",
                    "res_model": model,
                    "view_mode": "form",
                }
            )
            url = f"/odoo/action-{action.id}/{identity.id}"
            self.start_tour(url, "solution_stable_discussion", login=reader.login)
            messages = self.env["mail.message"].search(
                [
                    ("model", "=", model),
                    ("res_id", "=", identity.id),
                    ("body", "ilike", "Browser persistent discussion"),
                ]
            )
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages.author_id, reader.partner_id)
            self.browser_js(
                url,
                "console.log('test successful');",
                ready=(
                    "!!document.querySelector('.o-mail-Message-body')"
                    "?.textContent.includes('Browser persistent discussion')"
                ),
                login=reader.login,
            )
            self.authenticate(reader.login, reader.login)
            allowed = self._rpc("mail.message", "read", [messages.ids, ["body"]])
            self.assertIn("Browser persistent discussion", allowed["result"][0]["body"])
            fetch_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "id": 1,
                "params": {"thread_model": model, "thread_id": identity.id},
            }
            visible = self.url_open(
                "/mail/thread/messages",
                data=json.dumps(fetch_payload),
                headers={"Content-Type": "application/json"},
            )
            self.assertIn("Browser persistent discussion", visible.text)
            # Even a source reader cannot turn the administrative import API
            # into an RPC path for choosing another mail author.
            incoming = TestSolutionDiscussion._incoming_reply(
                self, messages.message_id, manager.email_formatted
            )
            import_denied = self._rpc(
                "mail.thread",
                "message_process",
                [None, incoming.as_string()],
                {"sudo": True, "_solution_gateway_reply": True},
            )
            self.assertEqual(
                import_denied["error"]["data"]["name"], "odoo.exceptions.AccessError"
            )
            self.assertFalse(
                self.env["mail.message"].search(
                    [
                        ("message_id", "=", incoming["Message-ID"]),
                    ]
                )
            )
            identity.message_subscribe(partner_ids=reader.partner_id.ids)
            follower = self.env["mail.followers"].search(
                [
                    ("res_model", "=", model),
                    ("res_id", "=", identity.id),
                    ("partner_id", "=", reader.partner_id.id),
                ]
            )
            self.assertTrue(follower)
            rule = self.env["ir.rule"].create(
                {
                    "name": "Revoke UI source",
                    "model_id": self.env["ir.model"]._get_id(model),
                    "domain_force": repr([("id", "!=", identity.id)]),
                }
            )
            self.env.flush_all()
            messages_response = self.url_open(
                "/mail/thread/messages",
                data=json.dumps(fetch_payload),
                headers={"Content-Type": "application/json"},
            )
            self.assertNotIn("Browser persistent discussion", messages_response.text)
            for target, method, args in (
                ("mail.message", "read", [messages.ids, ["body"]]),
                (model, "message_post", [identity.ids]),
                (model, "message_subscribe", [identity.ids, reader.partner_id.ids]),
            ):
                denied = self._rpc(target, method, args, {"sudo": True})
                self.assertEqual(
                    denied["error"]["data"]["name"], "odoo.exceptions.AccessError"
                )
                self.assertNotIn("Browser persistent discussion", str(denied))
            forged = self.url_open(
                "/web/dataset/call_kw",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "call",
                        "id": 1,
                        "params": {
                            "model": model,
                            "method": "message_post",
                            "args": [identity.ids],
                            "kwargs": {
                                "author_id": manager.partner_id.id,
                                "email_from": manager.email_formatted,
                                "message_type": "email",
                                "body": "RPC forgery",
                                "context": {
                                    "sudo": True,
                                    "_solution_gateway_reply": {"user_id": manager.id},
                                },
                            },
                        },
                    }
                ),
                headers={"Content-Type": "application/json"},
            ).json()
            self.assertEqual(
                forged["error"]["data"]["name"], "odoo.exceptions.AccessError"
            )
            self.assertNotIn("Browser persistent discussion", str(forged))
            native_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "id": 1,
                "params": {
                    "res_model": model,
                    "res_id": identity.id,
                    "partner_ids": manager.partner_id.ids,
                },
            }
            denied_removal = self.url_open(
                "/mail/thread/unsubscribe",
                data=json.dumps(native_payload),
                headers={"Content-Type": "application/json"},
            ).json()
            self.assertEqual(
                denied_removal["error"]["data"]["name"], "odoo.exceptions.AccessError"
            )
            self.assertTrue(follower.exists())
            native_payload["params"]["partner_ids"] = reader.partner_id.ids
            native_removed = self.url_open(
                "/mail/thread/unsubscribe",
                data=json.dumps(native_payload),
                headers={"Content-Type": "application/json"},
            ).json()
            self.assertIn("result", native_removed)
            self.assertNotIn("Browser persistent discussion", str(native_removed))
            self.assertNotIn("Shared native discussion", str(native_removed))
            self.assertFalse(follower.exists())
            removed = self._rpc(
                model,
                "message_unsubscribe",
                [identity.ids, reader.partner_id.ids],
                {"sudo": True, "_solution_gateway_reply": True},
            )
            # Native JSON-RPC omits the result key for a None return.
            self.assertEqual(removed["jsonrpc"], "2.0")
            self.assertEqual(removed["id"], 1)
            self.assertNotIn("error", removed)
            self.assertIsNone(removed.get("result"))
            self.assertFalse(follower.exists())
            still_hidden = self._rpc("mail.message", "read", [messages.ids, ["body"]])
            self.assertEqual(
                still_hidden["error"]["data"]["name"], "odoo.exceptions.AccessError"
            )
            self.assertNotIn("Browser persistent discussion", str(still_hidden))
            rule.unlink()

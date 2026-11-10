"""Explicit immutable customer disclosure; never a portal grant on source models."""

import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from odoo.addons.project_agile.utils import claim_records

from .solution_projection import (
    CUSTOMER_REQUIREMENT_FIELDS,
    audience_rows,
    narrative_text,
)

INTERNAL = "project.group_project_user"
STORAGE = "project_agile_solution.group_snapshot_storage"


def released_payload(revision):
    """Allowlist disclosed bytes, including nested requirement context."""
    source = revision._render_payload()
    names = CUSTOMER_REQUIREMENT_FIELDS
    requirements = audience_rows(source.get("requirements", []), "customer")
    members = {row["key"]: row["revision_id"] for row in requirements}
    contexts = []
    for row in audience_rows(
        source.get("contexts", []), "customer", ("question", "decision", "actor")
    ):
        contexts.append(
            {
                "title": row["title"],
                "kind": row["kind"],
                "text": narrative_text(row["body"]),
                "evaluation_expectations": row.get("evaluation_expectations") or "",
                "requirements": [
                    {name: item[name] for name in names}
                    for item in row.get("affected_requirements", [])
                    if item["audience"] == "customer" and item["key"] in members
                ],
            }
        )
    payload = {
        name: source[name]
        for name in (
            "title",
            "document_name",
            "project_name",
            "solution_name",
            "number",
            "kind",
        )
    }
    payload.update(
        schema=1,
        sections=[
            {"title": row["title"], "text": narrative_text(row["body"])}
            for row in audience_rows(source["sections"], "customer")
        ],
        requirements=[{name: row[name] for name in names} for row in requirements],
        contexts=contexts,
    )
    return payload, members


class SolutionPortalPublication(models.Model):
    _name = "project.agile.solution.portal.publication"
    _description = "Explicit Customer Revision Publication"
    _order = "id desc"
    _log_access = False

    name = fields.Char(required=True, readonly=True)
    revision_id = fields.Many2one(
        "project.agile.solution.revision",
        required=True,
        ondelete="restrict",
        readonly=True,
        groups=INTERNAL,
        index=True,
    )
    document_id = fields.Many2one(
        related="revision_id.document_id",
        store=True,
        groups=INTERNAL,
        index=True,
    )
    project_id = fields.Many2one(
        related="revision_id.project_id",
        store=True,
        groups=INTERNAL,
        index=True,
    )
    company_id = fields.Many2one(
        related="project_id.company_id",
        store=True,
        groups=INTERNAL,
    )
    recipient_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        readonly=True,
        groups=INTERNAL,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="restrict",
        readonly=True,
        groups=INTERNAL,
        index=True,
    )
    payload_json = fields.Text(required=True, readonly=True)
    payload_sha256 = fields.Char(required=True, readonly=True)
    snapshot_sha256 = fields.Char(required=True, readonly=True, groups=INTERNAL)
    _member_map = fields.Json(groups=STORAGE)
    published_by_id = fields.Many2one(
        "res.users",
        required=True,
        readonly=True,
        ondelete="restrict",
        groups=INTERNAL,
    )
    published_at = fields.Datetime(required=True, readonly=True)
    revoked_at = fields.Datetime(readonly=True)
    revoked_by_id = fields.Many2one(
        "res.users",
        readonly=True,
        ondelete="restrict",
        groups=INTERNAL,
    )
    _decision_head_id = fields.Many2one(
        "project.agile.solution.portal.document.decision",
        groups=STORAGE,
        ondelete="set null",
        copy=False,
    )
    _requirement_head_id = fields.Many2one(
        "project.agile.requirement.acceptance",
        groups=STORAGE,
        ondelete="set null",
        help=(
            "Written with requirement decisions to conflict "
            "with publication revocation."
        ),
    )
    document_decision_ids = fields.One2many(
        "project.agile.solution.portal.document.decision",
        "publication_id",
        readonly=True,
        groups=INTERNAL,
    )
    available = fields.Boolean(search="_search_available", compute="_compute_available")

    def _compute_available(self):
        visible = self.sudo(False).search([("id", "in", self.ids)])
        for row in self:
            row.available = row in visible

    def _search_available(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        caller = self.sudo(False)
        user = caller.env.user
        projects = caller.env["project.project"].with_context(active_test=False)
        if not user.active:
            access = Domain.FALSE
        elif user.has_group(INTERNAL):
            revisions = caller.env["project.agile.solution.revision"]
            access = Domain("revision_id", "in", revisions._search([]))
        elif user.has_group("base.group_portal") and user.partner_id.active:
            access = Domain.AND(
                [
                    Domain("recipient_id", "=", user.id),
                    Domain("partner_id", "=", user.partner_id.id),
                    Domain("revoked_at", "=", False),
                    Domain(
                        "project_id",
                        "in",
                        projects._search(
                            [
                                ("active", "=", True),
                                ("agile_enabled", "=", True),
                                ("message_partner_ids", "in", user.partner_id.ids),
                                ("company_id", "in", user.company_ids.ids + [False]),
                            ]
                        ),
                    ),
                    Domain("revision_id.state", "in", ["approved", "superseded"]),
                    Domain("revision_id.solution_id.active", "=", True),
                    Domain("document_id.active", "=", True),
                ]
            )
        else:
            access = Domain.FALSE
        positive = Domain.OR(
            access if item is True else ~access for item in value if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    @api.model_create_multi
    def create(self, vals_list):  # pylint: disable=method-required-super
        raise AccessError(
            _("Issue a publication explicitly from an approved revision.")
        )

    def write(self, values):  # pylint: disable=method-required-super
        raise AccessError(_("Released publications cannot be rewritten."))

    def unlink(self):  # pylint: disable=method-required-super
        # Immutable audit history is intentionally not deletable through the ORM.
        raise AccessError(_("Retain released publication history."))  # pylint: disable=no-raise-unlink

    def copy(self, default=None):  # pylint: disable=method-required-super
        raise AccessError(_("Issue a new publication deliberately."))

    def _check_read(self):
        caller = self.sudo(False)
        if caller.search_count([("id", "in", caller.ids)]) != len(caller):
            raise AccessError(
                _("This publication is unavailable under current access.")
            )
        caller.check_access("read")
        return caller

    def read(self, fields=None, load="_classic_read"):
        self._check_read()
        return super().read(fields, load=load)

    def export_data(self, fields_to_export):
        self._check_read()
        return super().export_data(fields_to_export)

    def _revoke(self):
        """Private revoke-only seam used by already-authorized native mutations."""
        live = self.sudo().filtered(lambda row: not row.revoked_at)
        if not live:
            return True
        claim_records(live, allow_referencing=True)
        return super(SolutionPortalPublication, live).write(
            {
                "revoked_at": fields.Datetime.now(),
                "revoked_by_id": self.env.uid,
            }
        )

    def action_revoke(self):
        for row in self._check_read():
            row.revision_id._check_authority(approval=True)
        self._revoke()
        return True

    def _can_decide(self):
        """Observational current-caller eligibility; never a grant or a claim."""
        self.ensure_one()
        caller = self.sudo(False)
        user = caller.env.user
        if (
            any(key.startswith("default_") for key in caller.env.context)
            or not user.share
            or not user.has_group("base.group_portal")
        ):
            return False
        # Reuse native recipient/contact/company/source and invitation rules.
        if not caller.search_count([("id", "=", caller.id)]):
            return False
        released = caller.sudo()
        return (
            released.revision_id.state == "approved"
            and released.document_id.portal_approver_id == user
            and released.recipient_id == user
            and released.partner_id == user.partner_id
            and not released.revoked_at
        )

    def _decision_caller(self):
        self.ensure_one()
        caller = self._check_read()
        if any(key.startswith("default_") for key in caller.env.context):
            raise ValidationError(_("Decision defaults are not accepted."))
        released = caller.sudo()
        claim_records(released, allow_referencing=True)
        released.revision_id._claim_portal_sources()
        if not caller._can_decide():
            raise AccessError(_("Only the current designated client may decide."))
        return caller

    def action_view(self):
        """Own receipt only, with no source relations or other recipients notes."""
        self.ensure_one()
        caller = self._check_read()
        released = caller.sudo()
        document = released._decision_head_id
        events = caller.env["project.agile.requirement.acceptance"].sudo()
        heads = {
            str(requirement.id): events.browse(event_id)
            for requirement, event_id in events._read_group(
                [
                    ("publication_id", "=", caller.id),
                    ("decision_source", "=", "portal"),
                ],
                ["requirement_revision_id"],
                ["id:max"],
            )
        }
        return {
            "payload": json.loads(caller.payload_json),
            "current": released.revision_id.state == "approved",
            "can_decide": caller._can_decide(),
            "document": document._receipt() if document else {"id": False},
            "requirements": {
                key: heads[str(record_id)]._portal_receipt()
                if str(record_id) in heads
                else {"id": False}
                for key, record_id in (released._member_map or {}).items()
            },
        }

    def action_decide_document(self, decision, expected_event_id=False, comment=""):
        caller = self._decision_caller()
        if decision not in ("approved", "rejected"):
            raise ValidationError(_("Choose Approve or Reject."))
        if type(comment) is not str or len(comment) > 10000:
            raise ValidationError(_("Use a bounded decision comment."))
        released = caller.sudo()
        previous = released._decision_head_id
        caller._check_expected(expected_event_id, previous.id)
        event = caller.env["project.agile.solution.portal.document.decision"]._append(
            released, decision, comment, previous
        )
        super(SolutionPortalPublication, released).write(
            {"_decision_head_id": event.id}
        )
        return event._receipt()

    def action_decide_requirement(
        self,
        key,
        number,
        decision,
        criteria_evaluated,
        evidence,
        expected_event_id=False,
    ):
        caller = self._decision_caller()
        released = caller.sudo()
        if type(key) is not str or type(number) is not int:
            raise ValidationError(_("Choose an exact published requirement revision."))
        record_id = (released._member_map or {}).get(key)
        if not record_id:
            raise AccessError(_("This requirement was not published to you."))
        requirement = (
            caller.env["project.agile.requirement.revision"].sudo().browse(record_id)
        )
        claim_records(requirement, allow_referencing=True)
        if requirement.number != number or released.revision_id.kind != "spec":
            raise ValidationError(_("Choose an exact published specification member."))
        if decision not in ("accepted", "rejected"):
            raise ValidationError(_("Choose Accept or Reject."))
        event = caller.env["project.agile.requirement.acceptance"]._append_portal(
            released,
            requirement,
            decision,
            criteria_evaluated,
            evidence,
            expected_event_id,
        )
        super(SolutionPortalPublication, released).write(
            {"_requirement_head_id": event.id}
        )
        return event._portal_receipt()

    def _check_expected(self, expected, actual):
        if not (expected is False or type(expected) is int and expected > 0):
            raise ValidationError(_("Use the decision shown on the current page."))
        if (expected or False) != (actual or False):
            raise ValidationError(
                _("The decision changed. Reload before correcting it.")
            )


class SolutionPortalRevision(models.Model):
    # Publication is a distinct audience boundary, not internal coverage ownership.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "project.agile.solution.revision"

    def action_portal_preview(self):
        self._check_authority(approval=True)
        if self.state != "approved":
            raise ValidationError(_("Publish only an internally approved revision."))
        return released_payload(self)[0]

    def action_request_publication(self):
        self.ensure_one()
        self.action_portal_preview()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "target": "new",
            "res_model": "project.agile.solution.portal.issue.wizard",
            "context": {"default_revision_id": self.id},
        }

    def _claim_portal_sources(self):
        """After caller authorization, order portal work against owner changes.

        Native owner writes conflict with these claims even after committing
        against an older REPEATABLE READ snapshot. Native transaction retry then
        rechecks availability; temporary archives do not revoke released grants.
        """
        self.ensure_one()
        source = self.sudo()
        claim_records(source.solution_id, allow_referencing=True)
        claim_records(source.project_id, allow_referencing=True)
        claim_records(source.document_id, allow_referencing=True)
        claim_records(source, allow_referencing=True)

    def action_issue_portal(self, recipient_id):
        self.ensure_one()
        self._check_authority(approval=True)
        self._claim_portal_sources()
        self.action_portal_preview()
        payload, members = released_payload(self)
        if type(recipient_id) is not int or recipient_id <= 0:
            raise ValidationError(_("Select an exact portal user."))
        recipient = self.env["res.users"].browse(recipient_id).exists()
        recipient.check_access("read")
        project = self.project_id
        if (
            not recipient
            or not recipient.active
            or not recipient.share
            or not recipient.has_group("base.group_portal")
            or not recipient.partner_id.active
            or recipient.partner_id not in project.message_partner_ids
            or project.company_id
            and project.company_id not in recipient.company_ids
            or not project.active
            or not project.agile_enabled
            or not self.solution_id.active
            or not self.document_id.active
        ):
            raise AccessError(
                _("Invite an active exact client contact to this Project.")
            )
        project.with_user(recipient).check_access("read")
        # Only this exact native invitation may coordinate the authorized issue.
        invitation = (
            self.env["mail.followers"]
            .sudo()
            .search(
                [
                    ("res_model", "=", "project.project"),
                    ("res_id", "=", project.id),
                    ("partner_id", "=", recipient.partner_id.id),
                ]
            )
        )
        if not invitation:
            raise AccessError(
                _("Invite an active exact client contact to this Project.")
            )
        claim_records(invitation, allow_referencing=True)
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        model = self.env["project.agile.solution.portal.publication"].sudo()
        # Exact server fields; discard caller defaults rather than merge context.
        model = model.with_context({})  # pylint: disable=context-overridden
        model.search(
            [
                ("revision_id", "=", self.id),
                ("recipient_id", "=", recipient.id),
                ("revoked_at", "=", False),
            ]
        )._revoke()
        publication = super(SolutionPortalPublication, model).create(
            {
                "name": payload["document_name"] + " / " + str(payload["number"]),
                "revision_id": self.id,
                "recipient_id": recipient.id,
                "partner_id": recipient.partner_id.id,
                "payload_json": raw,
                "payload_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "snapshot_sha256": self.snapshot_sha256,
                "_member_map": members,
                "published_by_id": self.env.uid,
                "published_at": fields.Datetime.now(),
                "revoked_at": False,
                "revoked_by_id": False,
                "_decision_head_id": False,
            }
        )
        # A real issued reference changes the invitation row, so an old-snapshot
        # native remover must retry even when no grant existed in its snapshot.
        invitation.write({"_portal_publication_head_id": publication.id})
        return publication.id


class SolutionPortalInvitation(models.Model):
    # Publication locking is separate from discussion and grant revocation.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "mail.followers"

    _portal_publication_head_id = fields.Many2one(
        "project.agile.solution.portal.publication",
        groups=STORAGE,
        copy=False,
        ondelete="set null",
        help=(
            "Written with each publication to conflict with native invitation "
            "removal and reassignment."
        ),
    )

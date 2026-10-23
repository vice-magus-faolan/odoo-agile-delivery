"""Separate append-only client document decisions; internal approval is unchanged."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class SolutionPortalDocumentDecision(models.Model):
    _name = "project.agile.solution.portal.document.decision"
    _description = "Authenticated Client Document Decision"
    _order = "id desc"
    _rec_name = "actor_label"

    publication_id = fields.Many2one(
        "project.agile.solution.portal.publication",
        required=True,
        ondelete="restrict",
        readonly=True,
        index=True,
    )
    revision_id = fields.Many2one(
        related="publication_id.revision_id",
        store=True,
    )
    payload_sha256 = fields.Char(required=True, readonly=True)
    actor_id = fields.Many2one(
        "res.users", required=True, ondelete="restrict", readonly=True
    )
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="restrict",
        readonly=True,
    )
    actor_label = fields.Char(required=True, readonly=True)
    recorded_at = fields.Datetime(required=True, readonly=True)
    decision = fields.Selection(
        [("approved", "Approved"), ("rejected", "Rejected")],
        required=True,
        readonly=True,
    )
    comment = fields.Text(readonly=True)
    supersedes_id = fields.Many2one(
        "project.agile.solution.portal.document.decision",
        readonly=True,
        ondelete="restrict",
    )

    @api.model_create_multi
    def create(self, vals_list):  # pylint: disable=method-required-super
        raise AccessError(_("Decide through your exact publication."))

    def _append(self, publication, decision, comment, previous):
        # Caller has checked and claimed the exact publication and current signer.
        model = self.sudo().with_context({})  # pylint: disable=context-overridden
        return super(SolutionPortalDocumentDecision, model).create(
            {
                "publication_id": publication.id,
                "payload_sha256": publication.payload_sha256,
                "actor_id": self.env.uid,
                "partner_id": self.env.user.partner_id.id,
                "actor_label": self.env.user.display_name,
                "recorded_at": fields.Datetime.now(),
                "decision": decision,
                "comment": comment,
                "supersedes_id": previous.id or False,
            }
        )

    def _receipt(self):
        self.ensure_one()
        return {
            "id": self.id,
            "decision": self.decision,
            "actor": self.actor_label,
            "time": fields.Datetime.to_string(self.recorded_at),
            "comment": self.comment or "",
        }

    def write(self, values):  # pylint: disable=method-required-super
        raise AccessError(_("Client decisions cannot be rewritten."))

    def unlink(self):  # pylint: disable=method-required-super
        # Immutable audit history is intentionally not deletable through the ORM.
        raise AccessError(_("Retain client decision history."))  # pylint: disable=no-raise-unlink

    def copy(self, default=None):  # pylint: disable=method-required-super
        raise AccessError(_("Append a deliberate client decision instead."))

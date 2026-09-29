"""Internal GitHub ingress persistence helpers for the provider-neutral ledger."""

import json

from psycopg2 import IntegrityError

from odoo import api, fields, models


MAX_RETAINED_PAYLOAD_CHARS = 4096
MAX_RETAINED_COLLECTION_ITEMS = 100
MAX_RETAINED_NESTING = 20
RETAINED_PAYLOAD_DAYS = 30
_SENSITIVE_KEY_PARTS = ("authorization", "password", "secret", "signature", "token")


def _redact_payload_value(value, depth=0):
    """Return a bounded, credential-scrubbed value safe for a retained excerpt."""

    if depth >= MAX_RETAINED_NESTING:
        return "[truncated]"
    if isinstance(value, dict):
        redacted = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_RETAINED_COLLECTION_ITEMS:
                redacted["[truncated]"] = "[truncated]"
                break
            key = str(key)
            if any(part in key.lower() for part in _SENSITIVE_KEY_PARTS):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_payload_value(item, depth + 1)
        return redacted
    if isinstance(value, list):
        redacted = [
            _redact_payload_value(item, depth + 1)
            for item in value[:MAX_RETAINED_COLLECTION_ITEMS]
        ]
        if len(value) > MAX_RETAINED_COLLECTION_ITEMS:
            redacted.append("[truncated]")
        return redacted
    return value


class ProjectGitRepository(models.Model):
    """Keep the public ingress lookup narrow and independent of caller company context."""

    _inherit = "project.git.repository"

    @api.model
    def _github_ingress_configuration(self, provider_repository_id):
        """Return active GitHub ingress configuration without exposing it through the ORM.

        A public webhook has no Project ACL. This parameterized internal lookup is
        deliberately limited to a globally unique provider identity and returns no
        data to the HTTP caller. It does not use caller-selected company/project
        context or elevate an Odoo user to make an authorization decision.
        """

        self.env.cr.execute(
            """
            SELECT id, webhook_secret, retention_policy
              FROM project_git_repository
             WHERE provider = %s
               AND provider_repository_id = %s
               AND active
             LIMIT 1
            """,
            ("github", provider_repository_id),
        )
        row = self.env.cr.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "webhook_secret": row[1],
            "retention_policy": row[2],
        }

    @api.model
    def _redacted_github_payload_excerpt(self, payload):
        """Serialize one bounded redacted payload excerpt without preserving raw bytes."""

        excerpt = json.dumps(
            _redact_payload_value(payload), ensure_ascii=True, separators=(",", ":")
        )
        return excerpt[:MAX_RETAINED_PAYLOAD_CHARS]


class ProjectGitDelivery(models.Model):
    """Create only the already-authenticated GitHub ledger record, idempotently."""

    _inherit = "project.git.delivery"

    @api.model
    def _record_authenticated_github_delivery(
        self,
        repository_id,
        provider_delivery_id,
        event_type,
        payload_sha256,
        payload_size,
        retained_payload=None,
    ):
        """Persist one authenticated delivery without normalizing or mutating workflow state.

        Elevation is deliberately after the controller's HMAC check. It only lets
        the server create its protected ledger record; it is never used to grant
        an HTTP caller access or decide whether that caller is authorized.
        """

        values = {
            "repository_id": repository_id,
            "provider_delivery_id": provider_delivery_id,
            "event_type": event_type,
            "payload_sha256": payload_sha256,
            "payload_size": payload_size,
            "retained_payload": retained_payload,
            "retained_until": (
                fields.Datetime.add(fields.Datetime.now(), days=RETAINED_PAYLOAD_DAYS)
                if retained_payload is not None
                else False
            ),
        }
        try:
            with self.env.cr.savepoint():
                return self.sudo().create(values), True
        except IntegrityError as error:
            if error.diag.constraint_name != "project_git_delivery_delivery_unique":
                raise
            delivery = self.sudo().search(
                [
                    ("repository_id", "=", repository_id),
                    ("provider_delivery_id", "=", provider_delivery_id),
                ],
                limit=1,
            )
            return delivery, False

"""Internal GitHub ingress persistence helpers for the provider-neutral ledger."""

import hashlib
import hmac
import json
import re

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.tools import SQL


MAX_RETAINED_PAYLOAD_CHARS = 4096
MAX_RETAINED_COLLECTION_ITEMS = 100
MAX_RETAINED_NESTING = 20
RETAINED_PAYLOAD_DAYS = 30
_SENSITIVE_KEY_PARTS = ("authorization", "password", "secret", "signature", "token")
MAX_REPLAY_MISMATCH_COUNT = 100
_SCALAR_REDACTION_PATTERNS = (
    (
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+"),
        r"\1[redacted]",
    ),
    (
        re.compile(r"(?i)\b(api[_ -]?key|token|secret|password)\s*([:=])\s*[^\s,;]+"),
        r"\1\2[redacted]",
    ),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[redacted]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[redacted]"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "[redacted]"),
)


def _redact_scalar_text(value):
    """Redact recognized credentials embedded in otherwise allowed scalar text."""

    for pattern, replacement in _SCALAR_REDACTION_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


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
    return _redact_scalar_text(value) if isinstance(value, str) else value


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
        """Return one valid bounded redacted payload, or no payload when it cannot fit safely."""

        excerpt = json.dumps(
            _redact_payload_value(payload), ensure_ascii=True, separators=(",", ":")
        )
        return excerpt if len(excerpt) <= MAX_RETAINED_PAYLOAD_CHARS else False


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
        retention_error=None,
        return_replay_status=False,
    ):
        """Persist one authenticated delivery without normalizing or mutating workflow state.

        Elevation is deliberately after the controller's HMAC check. It only lets
        the server create its protected ledger record; it is never used to grant
        an HTTP caller access or decide whether that caller is authorized. A
        valid but non-retainable excerpt is terminal so the worker cannot retry
        indefinitely after privacy-safe truncation rejected its raw payload.
        """

        def result(delivery, created, exact_replay):
            if return_replay_status:
                return delivery, created, exact_replay
            return delivery, created

        values = {
            "repository_id": repository_id,
            "provider_delivery_id": provider_delivery_id,
            "state": "failed" if retention_error else "queued",
            "event_type": event_type,
            "payload_sha256": payload_sha256,
            "payload_size": payload_size,
            "retained_payload": retained_payload,
            "retained_until": (
                fields.Datetime.add(fields.Datetime.now(), days=RETAINED_PAYLOAD_DAYS)
                if retained_payload
                else False
            ),
            "error_summary": retention_error,
            "last_error_at": fields.Datetime.now() if retention_error else False,
        }
        try:
            with self.env.cr.savepoint():
                return result(self.sudo().create(values), True, True)
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
            if not delivery:
                raise
            exact_replay = (
                delivery.event_type == event_type
                and delivery.payload_size == payload_size
                and hmac.compare_digest(delivery.payload_sha256, payload_sha256)
            )
            if not exact_replay:
                self.env.cr.execute(
                    SQL(
                        """
                        UPDATE project_git_delivery
                           SET replay_mismatch_count = LEAST(replay_mismatch_count + 1, %s),
                               last_replay_mismatch_at = NOW()
                         WHERE id = %s
                        """,
                        MAX_REPLAY_MISMATCH_COUNT,
                        delivery.id,
                    )
                )
                delivery.invalidate_recordset(
                    ["replay_mismatch_count", "last_replay_mismatch_at"]
                )
            return result(delivery, False, exact_replay)

"""Internal GitHub ingress persistence helpers for the provider-neutral ledger."""

import hmac
import json
import re

from psycopg2 import IntegrityError

from odoo import api, fields, models

MAX_RETAINED_PAYLOAD_CHARS = 4096
MAX_RETAINED_COLLECTION_ITEMS = 100
RETAINED_PAYLOAD_DAYS = 30
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


# These are the normalizer inputs, not a subset of arbitrary provider metadata.
# Missing fields stay missing so native validation/defaults retain their meaning.
_EVENT_INPUTS = {
    "push": {
        "ref": None,
        "after": None,
        "head_commit": {"timestamp": None},
        "commits": [{"id": None, "message": None, "timestamp": None}],
    },
    "pull_request": {
        "number": None,
        "pull_request": {
            "id": None,
            "title": None,
            "body": None,
            "state": None,
            "merged": None,
            "merged_at": None,
            "updated_at": None,
            "head": {"ref": None, "sha": None},
            "base": {"ref": None},
        },
    },
    "check_run": {
        "check_run": {
            "id": None,
            "name": None,
            "status": None,
            "conclusion": None,
            "head_sha": None,
            "completed_at": None,
            "updated_at": None,
            "output": {"title": None},
        },
    },
}


def _project_payload_value(value, shape):
    """Select consumer inputs without truncating collections or source text."""

    if isinstance(shape, dict):
        if not isinstance(value, dict):
            raise ValueError("Malformed GitHub input object.")
        return {
            key: _project_payload_value(value[key], child)
            for key, child in shape.items()
            if key in value
        }
    if isinstance(shape, list):
        if not isinstance(value, list) or len(value) > MAX_RETAINED_COLLECTION_ITEMS:
            raise ValueError("Malformed or oversized GitHub input collection.")
        return [_project_payload_value(item, shape[0]) for item in value]
    if isinstance(value, (dict, list)):
        raise ValueError("Malformed GitHub scalar input.")
    return _redact_scalar_text(value) if isinstance(value, str) else value


class ProjectGitRepository(models.Model):
    """Keep the public ingress lookup narrow and independent of caller company
    context.
    """

    _inherit = "project.git.repository"

    @api.model
    def _github_ingress_configuration(self, provider_repository_id):
        """Return only the server-side configuration for an active GitHub identity.

        The public webhook has no Project ACL. This private lookup elevates only
        to read the globally unique provider configuration, ignoring caller
        context. Nothing is returned to the HTTP caller; the controller must
        still authenticate the exact body with this repository-specific secret
        before recording a delivery. ORM privilege is not webhook authentication.
        """

        repository = self.sudo().search(
            [
                ("provider", "=", "github"),
                ("provider_repository_id", "=", provider_repository_id),
                ("active", "=", True),
            ],
            limit=1,
        )
        if not repository:
            return None
        return {
            "id": repository.id,
            "webhook_secret": repository.webhook_secret,
            "retention_policy": repository.retention_policy,
        }

    @api.model
    def _redacted_github_payload_excerpt(self, payload, event_type):
        """Retain only credential-scrubbed normalizer inputs within the fixed cap.

        Reject an intrinsically oversized or malformed projection as a whole:
        cutting text or commits could silently lose facts or explicit task keys.
        Unsupported events need only repository identity for terminal diagnostics.
        """

        shape = {"repository": {"id": None}, **_EVENT_INPUTS.get(event_type, {})}
        try:
            projection = _project_payload_value(payload, shape)
        except ValueError:
            return False
        excerpt = json.dumps(projection, ensure_ascii=True, separators=(",", ":"))
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
        """Persist one authenticated delivery without normalizing or mutating
        workflow state.

        Elevation is deliberately after the controller's HMAC check. It only lets
        the server create its protected ledger record; it is never used to grant
        an HTTP caller access or decide whether that caller is authorized. A
        valid but non-retainable excerpt is terminal so the worker cannot retry
        indefinitely after its required processing input could not be retained.
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
                # A competing ORM write conflicts under repeatable read; let
                # the native request retry restart the entire transaction rather
                # than accepting a lost increment from an old snapshot.
                delivery.write(
                    {
                        "replay_mismatch_count": min(
                            delivery.replay_mismatch_count + 1,
                            MAX_REPLAY_MISMATCH_COUNT,
                        ),
                        "last_replay_mismatch_at": fields.Datetime.now(),
                    }
                )
            return result(delivery, False, exact_replay)

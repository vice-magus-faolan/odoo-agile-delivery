"""Internal GitHub ingress persistence helpers for the provider-neutral ledger."""

import hmac
import json
import re

from psycopg2 import IntegrityError

from odoo import api, fields, models

from .github_keys import (
    MAX_PROVIDER_COMMITS,
    MAX_RETAINED_COMMITS,
    source_key_summary,
)

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


def _compact_source(value, with_excerpt=False):
    """Extract keys before display truncation, after credential scrubbing."""

    if value is None and not with_excerpt:
        value = ""
    if not isinstance(value, str):
        raise ValueError("Malformed GitHub source text.")
    value = _redact_scalar_text(value)
    summary = source_key_summary(value)
    if with_excerpt:
        summary["excerpt"] = value[:255]
    return summary


def _compact_message(value):
    """Retain the message display excerpt and full-source key evidence."""

    return _compact_source(value, with_excerpt=True)


# Scalar limits count characters before JSON escaping. Missing fields stay
# missing so native validation/defaults retain their meaning. Callable shapes
# accept provider text only, never caller-supplied compact evidence.
_EVENT_INPUTS = {
    "push": {
        "ref": 4096,
        "after": 128,
        "head_commit": {"timestamp": 64},
        "commits": [{"id": 128, "message": _compact_message, "timestamp": 64}],
    },
    "pull_request": {
        "number": 64,
        "pull_request": {
            "id": 128,
            "title": 4096,
            "body": _compact_source,
            "state": 32,
            "merged": 32,
            "merged_at": 64,
            "updated_at": 64,
            "head": {"ref": 4096, "sha": 128},
            "base": {"ref": 4096},
        },
    },
    "check_run": {
        "check_run": {
            "id": 128,
            "name": 4096,
            "status": 32,
            "conclusion": 32,
            "head_sha": 128,
            "completed_at": 64,
            "updated_at": 64,
            "output": {"title": 4096},
        },
    },
}


def _project_payload_value(value, shape):
    """Select bounded consumer inputs, compacting only declared source text."""

    if isinstance(shape, dict):
        if not isinstance(value, dict):
            raise ValueError("Malformed GitHub input object.")
        return {
            key: _project_payload_value(value[key], child)
            for key, child in shape.items()
            if key in value
        }
    if isinstance(shape, list):
        if not isinstance(value, list) or len(value) > MAX_PROVIDER_COMMITS:
            raise ValueError("Malformed or oversized GitHub input collection.")
        return [
            _project_payload_value(item, shape[0])
            for item in value[:MAX_RETAINED_COMMITS]
        ]
    if callable(shape):
        return shape(value)
    if value is None:
        return None
    if not isinstance(value, (str, int)) or len(str(value)) > shape:
        raise ValueError("Malformed or oversized GitHub scalar input.")
    projected = _redact_scalar_text(value) if isinstance(value, str) else value
    if len(str(projected)) > shape:
        raise ValueError("Oversized redacted GitHub scalar input.")
    return projected


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
        """Retain finite semantic inputs, not arbitrary provider text/metadata.

        First 100 commit facts are retained; the exact omitted count travels
        separately so settlement can persist a manager-visible diagnostic.
        Unsupported events need only repository identity.
        """

        shape = {"repository": {"id": 128}, **_EVENT_INPUTS.get(event_type, {})}
        try:
            projection = _project_payload_value(payload, shape)
        except ValueError:
            return False
        if event_type == "push" and "commits" in projection:
            projection["omitted_commit_count"] = max(
                len(payload["commits"]) - MAX_RETAINED_COMMITS, 0
            )
        return json.dumps(projection, ensure_ascii=True, separators=(",", ":"))


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

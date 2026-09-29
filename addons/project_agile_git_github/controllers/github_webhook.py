"""Bounded authenticated GitHub delivery ingress."""

import hashlib
import hmac
import json
import re

from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response


MAX_BODY_BYTES = 256 * 1024
MAX_DELIVERY_ID_LENGTH = 128
MAX_EVENT_TYPE_LENGTH = 100
_SIGNATURE_PATTERN = re.compile(r"sha256=[0-9a-f]{64}")
_RETENTION_LIMIT_ERROR = "The signed payload exceeds the safe retained excerpt limit."


def _response(status):
    """Return an intentionally empty response without provider or secret detail."""

    return Response(status=status)


def _bounded_header(headers, name, maximum_length):
    """Return one bounded printable header value, or ``None`` when it is invalid."""

    value = headers.get(name)
    if not value or len(value) > maximum_length or not value.isprintable():
        return None
    return value


def _github_repository_id(payload):
    """Extract GitHub's immutable repository identity from a validated JSON object."""

    if not isinstance(payload, dict):
        return None
    repository = payload.get("repository")
    if not isinstance(repository, dict):
        return None
    repository_id = repository.get("id")
    if isinstance(repository_id, bool) or not isinstance(repository_id, (int, str)):
        return None
    repository_id = str(repository_id)
    if not repository_id or len(repository_id) > MAX_DELIVERY_ID_LENGTH:
        return None
    return repository_id


class GitHubWebhookController(http.Controller):
    """Persist GitHub deliveries after bounded validation and exact-body authentication."""

    @http.route(
        "/project_agile_git_github/webhook",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def github_webhook(self):
        """Validate one GitHub delivery and durably record it without processing its facts."""

        httprequest = request.httprequest
        if httprequest.mimetype != "application/json":
            return _response(415)
        if httprequest.content_length is None or httprequest.content_length > MAX_BODY_BYTES:
            return _response(413)

        raw_body = httprequest.get_data(cache=True)
        if len(raw_body) > MAX_BODY_BYTES:
            return _response(413)
        event_type = _bounded_header(
            httprequest.headers, "X-GitHub-Event", MAX_EVENT_TYPE_LENGTH
        )
        provider_delivery_id = _bounded_header(
            httprequest.headers, "X-GitHub-Delivery", MAX_DELIVERY_ID_LENGTH
        )
        provided_signature = httprequest.headers.get("X-Hub-Signature-256")
        if not event_type or not provider_delivery_id or not _SIGNATURE_PATTERN.fullmatch(
            provided_signature or ""
        ):
            return _response(400)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _response(400)
        repository_id = _github_repository_id(payload)
        if not repository_id:
            return _response(400)

        repository_model = request.env["project.git.repository"]
        ingress = repository_model._github_ingress_configuration(repository_id)
        if not ingress or not ingress["webhook_secret"]:
            return _response(401)
        expected_signature = "sha256=" + hmac.new(
            ingress["webhook_secret"].encode(), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(provided_signature, expected_signature):
            return _response(401)

        retained_payload = None
        retention_error = None
        if ingress["retention_policy"] == "redacted_excerpt":
            retained_payload = repository_model._redacted_github_payload_excerpt(payload)
            if not retained_payload:
                retention_error = _RETENTION_LIMIT_ERROR
        request.env["project.git.delivery"]._record_authenticated_github_delivery(
            repository_id=ingress["id"],
            provider_delivery_id=provider_delivery_id,
            event_type=event_type,
            payload_sha256=hashlib.sha256(raw_body).hexdigest(),
            payload_size=len(raw_body),
            retained_payload=retained_payload,
            retention_error=retention_error,
        )
        return _response(202)

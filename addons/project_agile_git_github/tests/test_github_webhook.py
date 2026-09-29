"""End-to-end authenticated GitHub delivery ingress coverage."""

import hashlib
import hmac
import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestGitHubWebhook(HttpCase):
    """Exercise the public route without granting the HTTP caller any project access."""

    route = "/project_agile_git_github/webhook"
    secret = "fixture-github-secret"

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "GitHub ingress",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "GHI",
            }
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "ingress",
                "provider": "github",
                "provider_repository_id": "4242",
                "canonical_url": "https://example.invalid/acme/ingress",
                "project_id": self.project.id,
                "webhook_secret": self.secret,
            }
        )

    def _payload(self, repository_id="4242", **extra):
        return {"repository": {"id": repository_id, **extra}}

    def _post(self, payload, delivery_id="delivery-1", secret=None, **headers):
        raw_body = json.dumps(payload, separators=(",", ":")).encode()
        signing_secret = self.secret if secret is None else secret
        signature = "sha256=" + hmac.new(
            signing_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        request_headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": delivery_id,
            "X-Hub-Signature-256": signature,
            **headers,
        }
        return self.url_open(self.route, data=raw_body, headers=request_headers)

    def _delivery_count(self):
        return self.env["project.git.delivery"].search_count(
            [("repository_id", "=", self.repository.id)]
        )

    def test_valid_delivery_is_persisted_once_without_workflow_mutation(self):
        task = self.env["project.task"].create(
            {"name": "Must stay untouched", "project_id": self.project.id}
        )
        before = task.read(["stage_id", "message_partner_ids"])[0]

        response = self._post(self._payload(), delivery_id="delivery-valid")

        self.assertEqual(response.status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [("repository_id", "=", self.repository.id), ("provider_delivery_id", "=", "delivery-valid")]
        )
        self.assertEqual((delivery.state, delivery.attempt_count), ("received", 0))
        self.assertEqual(delivery.payload_sha256, hashlib.sha256(b'{"repository":{"id":"4242"}}').hexdigest())
        self.assertEqual(task.read(["stage_id", "message_partner_ids"])[0], before)

    def test_replay_returns_accepted_without_duplicate_ledger_work(self):
        response = self._post(self._payload(), delivery_id="delivery-replay")
        replay = self._post(self._payload(), delivery_id="delivery-replay")

        self.assertEqual((response.status_code, replay.status_code), (202, 202))
        self.assertEqual(self._delivery_count(), 1)

    def test_invalid_unknown_and_inactive_repositories_are_rejected(self):
        invalid = self._post(self._payload(), secret="wrong-secret")
        unknown = self._post(self._payload("9999"), delivery_id="delivery-unknown")
        self.repository.active = False
        inactive = self._post(self._payload(), delivery_id="delivery-inactive")

        self.assertEqual((invalid.status_code, unknown.status_code, inactive.status_code), (401, 401, 401))
        self.assertEqual(self._delivery_count(), 0)

    def test_cross_company_repository_requires_its_own_configured_secret(self):
        other_company = self.env["res.company"].create({"name": "Other company"})
        other_project = self.env["project.project"].with_company(other_company).create(
            {
                "name": "Other GitHub ingress",
                "company_id": other_company.id,
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "OTH",
            }
        )
        other_repository = self.env["project.git.repository"].create(
            {
                "name": "other-ingress",
                "provider": "github",
                "provider_repository_id": "4243",
                "canonical_url": "https://example.invalid/other/ingress",
                "project_id": other_project.id,
                "webhook_secret": "other-company-secret",
            }
        )

        response = self._post(
            self._payload("4243"), delivery_id="delivery-cross-company", secret=self.secret
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(
            self.env["project.git.delivery"].search(
                [("repository_id", "=", other_repository.id)]
            )
        )

    def test_malformed_oversized_and_unsupported_requests_are_rejected(self):
        malformed_body = b"{"
        malformed_signature = "sha256=" + hmac.new(
            self.secret.encode(), malformed_body, hashlib.sha256
        ).hexdigest()
        malformed = self.url_open(
            self.route,
            data=malformed_body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "push",
                "X-GitHub-Delivery": "delivery-malformed",
                "X-Hub-Signature-256": malformed_signature,
            },
        )
        unsupported = self._post(self._payload(), **{"Content-Type": "text/plain"})
        oversized = self.url_open(
            self.route,
            data=b"x" * (256 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual((malformed.status_code, unsupported.status_code, oversized.status_code), (400, 415, 413))
        self.assertEqual(self._delivery_count(), 0)

    def test_redacted_excerpt_never_retains_credential_shaped_payload_values(self):
        self.repository.retention_policy = "redacted_excerpt"

        response = self._post(
            self._payload(token="must-not-be-retained"), delivery_id="delivery-redacted"
        )

        self.assertEqual(response.status_code, 202)
        delivery = self.env["project.git.delivery"].search(
            [("repository_id", "=", self.repository.id), ("provider_delivery_id", "=", "delivery-redacted")]
        )
        self.assertIn("[redacted]", delivery.retained_payload)
        self.assertNotIn("must-not-be-retained", delivery.retained_payload)
        self.assertTrue(delivery.retained_until)

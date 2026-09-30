"""Retention cleanup coverage for bounded GitHub delivery evidence."""

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestGitHubDeliveryRetention(TransactionCase):
    """Keep terminal cleanup bounded without silently losing actionable evidence."""

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "GitHub retention",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "RET",
            }
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "retention",
                "provider": "github",
                "provider_repository_id": "6001",
                "canonical_url": "https://github.com/acme/retention",
                "project_id": self.project.id,
                "webhook_secret": "fixture-secret",
                "retention_policy": "redacted_excerpt",
            }
        )

    def _delivery(self, suffix, state, retained_until, retained_payload="{\"repository\":{\"id\":6001}}"):
        return self.env["project.git.delivery"].create(
            {
                "repository_id": self.repository.id,
                "provider_delivery_id": "retention-" + suffix,
                "event_type": "push",
                "payload_sha256": "a" * 64,
                "payload_size": 1,
                "state": state,
                "retained_payload": retained_payload,
                "retained_until": retained_until,
            }
        )

    def test_cleanup_purges_only_expired_terminal_payloads_and_keeps_ledger_rows(self):
        now = fields.Datetime.now()
        processed = self._delivery("processed", "processed", now - timedelta(days=1))
        discarded = self._delivery("discarded", "discarded", now - timedelta(days=1))
        queued = self._delivery("queued", "queued", now - timedelta(days=1))
        failed = self._delivery("failed", "failed", now - timedelta(days=1))
        future = self._delivery("future", "processed", now + timedelta(days=1))

        purged = self.env["project.git.delivery"]._purge_expired_github_payloads()
        self.env.invalidate_all()

        self.assertEqual(purged, 2)
        self.assertTrue(processed.exists())
        self.assertTrue(discarded.exists())
        self.assertFalse(processed.retained_payload)
        self.assertFalse(discarded.retained_payload)
        self.assertTrue(processed.retained_payload_purged_at)
        self.assertTrue(discarded.retained_payload_purged_at)
        self.assertTrue(queued.retained_payload)
        self.assertTrue(failed.retained_payload)
        self.assertTrue(future.retained_payload)
        self.assertFalse(queued.retained_payload_purged_at)
        self.assertFalse(failed.retained_payload_purged_at)

    def test_cleanup_rechecks_state_before_purging_a_stale_candidate(self):
        now = fields.Datetime.now()
        delivery = self._delivery("raced", "processed", now - timedelta(days=1))
        delivery.state = "queued"
        model = self.env["project.git.delivery"]

        with patch.object(type(model), "search", return_value=delivery):
            purged = model._purge_expired_github_payloads(now)

        self.assertEqual(purged, 0)
        self.assertTrue(delivery.retained_payload)
        self.assertFalse(delivery.retained_payload_purged_at)

    def test_oversized_redacted_excerpt_is_terminal_and_cannot_be_reprocessed(self):
        excerpt = self.repository._redacted_github_payload_excerpt(
            {"repository": {"id": 6001}, "description": "x" * 5000}
        )
        self.assertFalse(excerpt)

        delivery, created = self.env["project.git.delivery"]._record_authenticated_github_delivery(
            repository_id=self.repository.id,
            provider_delivery_id="retention-oversized",
            event_type="push",
            payload_sha256="b" * 64,
            payload_size=5000,
            retained_payload=excerpt,
            retention_error="The signed payload exceeds the safe retained excerpt limit.",
        )

        self.assertTrue(created)
        self.assertEqual(delivery.state, "failed")
        self.assertFalse(delivery.retained_payload)
        self.assertEqual(
            delivery.error_summary,
            "The signed payload exceeds the safe retained excerpt limit.",
        )
        with self.assertRaises(ValidationError):
            delivery.action_reprocess_github_delivery()

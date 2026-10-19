"""Retention cleanup coverage for bounded GitHub delivery evidence."""

import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.project_agile_git_github.models.project_github_retention import (
    RETENTION_CLEANUP_BATCH_SIZE,
)


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

    def _delivery(
        self,
        suffix,
        state,
        retained_until,
        retained_payload='{"repository":{"id":6001}}',
    ):
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
        processing = self._delivery("processing", "processing", now - timedelta(days=1))
        failed = self._delivery("failed", "failed", now - timedelta(days=1))
        future = self._delivery("future", "processed", now + timedelta(days=1))

        fenced = "git_policy_evidence_version" in self.repository._fields
        evidence_version = self.repository.git_policy_evidence_version if fenced else 0
        purged = self.env["project.git.delivery"]._purge_expired_github_payloads()
        self.env.invalidate_all()

        self.assertEqual(purged, 2)
        self.assertTrue(processed.exists())
        self.assertTrue(discarded.exists())
        self.assertFalse(processed.retained_payload)
        self.assertFalse(discarded.retained_payload)
        self.assertTrue(processed.retained_payload_purged_at)
        self.assertTrue(discarded.retained_payload_purged_at)
        self.assertTrue(processing.retained_payload)
        self.assertTrue(queued.retained_payload)
        self.assertTrue(failed.retained_payload)
        self.assertTrue(future.retained_payload)
        self.assertFalse(queued.retained_payload_purged_at)
        self.assertFalse(failed.retained_payload_purged_at)
        if fenced:
            self.assertGreater(
                self.repository.git_policy_evidence_version, evidence_version
            )
        purged_at = processed.retained_payload_purged_at
        self.assertEqual(
            self.env["project.git.delivery"]._purge_expired_github_payloads(), 0
        )
        self.assertEqual(processed.retained_payload_purged_at, purged_at)

    def test_oversized_redacted_excerpt_is_terminal_and_cannot_be_reprocessed(self):
        excerpt = self.repository._redacted_github_payload_excerpt(
            {"repository": {"id": 6001}, "ref": "x" * 5000}, "push"
        )
        self.assertFalse(excerpt)

        delivery, created = self.env[
            "project.git.delivery"
        ]._record_authenticated_github_delivery(
            repository_id=self.repository.id,
            provider_delivery_id="retention-oversized",
            event_type="push",
            payload_sha256="b" * 64,
            payload_size=5000,
            retained_payload=excerpt,
            retention_error=(
                "The signed payload has malformed or oversized processing input."
            ),
        )

        self.assertTrue(created)
        self.assertEqual(delivery.state, "failed")
        self.assertFalse(delivery.retained_payload)
        self.assertEqual(
            delivery.error_summary,
            "The signed payload has malformed or oversized processing input.",
        )
        with self.assertRaises(ValidationError):
            delivery.action_reprocess_github_delivery()

    def test_cleanup_is_bounded_and_cron_reports_progress(self):
        now = fields.Datetime.now()
        for index in range(RETENTION_CLEANUP_BATCH_SIZE + 1):
            self._delivery(str(index), "processed", now - timedelta(days=1))
        model = self.env["project.git.delivery"]
        cron = self.env["ir.cron"]
        with patch.object(type(cron), "_commit_progress") as progress:
            self.assertEqual(
                model._cron_purge_expired_github_payloads(),
                RETENTION_CLEANUP_BATCH_SIZE,
            )
            progress.assert_called_once_with(
                remaining=1, processed=RETENTION_CLEANUP_BATCH_SIZE
            )
        self.assertEqual(model._purge_expired_github_payloads(now), 1)
        self.assertEqual(model._purge_expired_github_payloads(now), 0)

    def test_projection_preserves_all_commits_or_rejects_the_collection(self):
        payload = {
            "repository": {"id": 6001},
            "commits": [{"id": str(index), "message": "RET-1"} for index in range(100)],
        }
        excerpt = self.repository._redacted_github_payload_excerpt(payload, "push")
        self.assertEqual(json.loads(excerpt)["commits"], payload["commits"])
        payload["commits"].append({"id": "100", "message": "RET-2"})
        self.assertFalse(
            self.repository._redacted_github_payload_excerpt(payload, "push")
        )

    def test_projection_rejects_malformed_nested_inputs_without_retaining_them(self):
        for event, extra in (
            ("push", {"commits": [{"message": {"secret": "private"}}]}),
            ("push", {"commits": "not-a-list"}),
            ("pull_request", {"pull_request": {"head": []}}),
            ("check_run", {"check_run": {"output": {"title": ["private"]}}}),
        ):
            with self.subTest(event=event, extra=extra):
                self.assertFalse(
                    self.repository._redacted_github_payload_excerpt(
                        {"repository": {"id": 6001}, **extra}, event
                    )
                )

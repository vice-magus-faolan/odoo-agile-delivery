"""Runtime coverage for native leased GitHub fact normalization."""

import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestGitHubDeliveryNormalization(TransactionCase):
    """Exercise fact idempotency, ordering, associations, and failure visibility."""

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Normalizer",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "NRM",
            }
        )
        self.first_task = self.env["project.task"].create(
            {"name": "First", "project_id": self.project.id}
        )
        self.second_task = self.env["project.task"].create(
            {"name": "Second", "project_id": self.project.id}
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "normalizer",
                "provider": "github",
                "provider_repository_id": "2001",
                "canonical_url": "https://example.invalid/acme/normalizer",
                "project_id": self.project.id,
                "webhook_secret": "fixture-secret",
                "retention_policy": "redacted_excerpt",
            }
        )

    def _delivery(self, event_type, payload, suffix):
        return self.env["project.git.delivery"].create(
            {
                "repository_id": self.repository.id,
                "provider_delivery_id": "delivery-" + suffix,
                "event_type": event_type,
                "payload_sha256": "a" * 64,
                "payload_size": 1,
                "retained_payload": json.dumps(payload),
                "state": "queued",
            }
        )

    def _process(self, delivery):
        claimed = self.env["project.git.delivery"]._claim_github_delivery()
        self.assertEqual(claimed, delivery)
        claimed._settle_github_delivery()
        self.env.invalidate_all()
        return delivery

    def _push(self, sha, timestamp, message):
        return {
            "repository": {"id": 2001},
            "ref": "refs/heads/feature/NRM-1-delivery",
            "after": sha,
            "head_commit": {"timestamp": timestamp},
            "commits": [
                {
                    "id": sha,
                    "message": message,
                    "timestamp": timestamp,
                    "url": "https://example.invalid/commit/" + sha,
                }
            ],
        }

    def test_push_creates_facts_and_exact_key_associations_without_task_mutation(self):
        before = self.first_task.read(["stage_id", "message_partner_ids"])[0]
        delivery = self._delivery(
            "push",
            self._push("a" * 40, "2026-01-02T03:04:05Z", "[NRM-1] implements parser"),
            "push",
        )

        self._process(delivery)

        branch = self.env["project.git.branch"].search([("repository_id", "=", self.repository.id)])
        commit = self.env["project.git.commit"].search([("repository_id", "=", self.repository.id)])
        association = self.env["project.git.task.association"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("task_id", "=", self.first_task.id),
                ("source_type", "=", "commit"),
            ]
        )
        self.assertEqual(delivery.state, "processed")
        self.assertEqual(branch.provider_branch_id, "refs/heads/feature/NRM-1-delivery")
        self.assertEqual(branch.head_sha, "a" * 40)
        self.assertEqual(commit.sha, "a" * 40)
        self.assertEqual(association.agile_key, self.first_task.agile_key)
        self.assertEqual(self.first_task.read(["stage_id", "message_partner_ids"])[0], before)

    def test_pull_request_preserves_multiple_explicit_key_decisions(self):
        delivery = self._delivery(
            "pull_request",
            {
                "repository": {"id": 2001},
                "number": 4,
                "pull_request": {
                    "id": 404,
                    "title": "[NRM-1] and NRM-2",
                    "body": "Unknown NRM-999 stays auditable",
                    "state": "open",
                    "merged": False,
                    "head": {"ref": "feature/NRM-2-work", "sha": "b" * 40},
                    "base": {"ref": "main"},
                    "html_url": "https://example.invalid/pr/4",
                    "updated_at": "2026-01-02T03:04:05Z",
                    "merged_at": None,
                },
            },
            "pull",
        )

        self._process(delivery)

        associations = self.env["project.git.task.association"].search(
            [("repository_id", "=", self.repository.id), ("source_type", "=", "pull_request")]
        )
        audits = self.env["project.git.association.audit"].search(
            [("delivery_id", "=", delivery.id), ("agile_key", "=", "NRM-999")]
        )
        self.assertEqual(set(associations.mapped("agile_key")), {"NRM-1", "NRM-2"})
        self.assertEqual((audits.outcome, audits.reason), ("unassociated", "unknown_key"))

    def test_out_of_order_push_does_not_regress_a_newer_branch_head(self):
        newer = self._delivery(
            "push", self._push("c" * 40, "2026-01-03T03:04:05Z", "NRM-1 newest"), "newer"
        )
        older = self._delivery(
            "push", self._push("d" * 40, "2026-01-01T03:04:05Z", "NRM-1 older"), "older"
        )

        self._process(newer)
        self._process(older)

        branch = self.env["project.git.branch"].search([("repository_id", "=", self.repository.id)])
        self.assertEqual(branch.head_sha, "c" * 40)
        self.assertEqual(branch.ordering_state, "stale")
        self.assertEqual((newer.state, older.state), ("processed", "processed"))

    def test_malformed_payload_rolls_back_partial_facts_and_dead_letters_delivery(self):
        delivery = self._delivery(
            "push",
            {
                "repository": {"id": 2001},
                "ref": "refs/heads/NRM-1-broken",
                "after": "e" * 40,
                "head_commit": {"timestamp": "2026-01-03T03:04:05Z"},
                "commits": [{"id": "e" * 40}],
            },
            "malformed",
        )

        self._process(delivery)

        self.assertEqual(delivery.state, "failed")
        self.assertFalse(self.env["project.git.branch"].search([("repository_id", "=", self.repository.id)]))
        self.assertTrue(delivery.error_summary)

    def test_mismatched_payload_repository_is_rejected_without_fact_writes(self):
        payload = self._push("e" * 40, "2026-01-03T03:04:05Z", "NRM-1 forged")
        payload["repository"]["id"] = 999999
        delivery = self._delivery("push", payload, "wrong-repository")

        self._process(delivery)

        self.assertEqual(delivery.state, "failed")
        self.assertIn("does not match", delivery.error_summary)
        self.assertFalse(self.env["project.git.branch"].search([("repository_id", "=", self.repository.id)]))

    def test_transient_failure_retries_then_dead_letters_after_the_bound(self):
        delivery = self._delivery("push", self._push("f" * 40, "2026-01-03T03:04:05Z", "NRM-1"), "retry")

        with patch.object(type(delivery), "_normalize_github_delivery", side_effect=RuntimeError("fixture")):
            for attempt in range(5):
                self._process(delivery)
                if attempt < 4:
                    self.assertEqual(delivery.state, "retryable")
                    delivery.next_retry_at = False

        self.assertEqual((delivery.state, delivery.attempt_count), ("failed", 5))
        self.assertEqual(delivery.error_summary, "GitHub fact normalization failed.")

    def test_unsupported_event_is_terminally_discarded(self):
        delivery = self._delivery("star", {"repository": {"id": 2001}}, "unsupported")

        self._process(delivery)

        self.assertEqual(delivery.state, "discarded")
        self.assertEqual(delivery.error_summary, "Unsupported GitHub event type.")

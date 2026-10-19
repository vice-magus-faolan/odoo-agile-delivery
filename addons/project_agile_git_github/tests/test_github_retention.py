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
        processed.write(
            {
                "omitted_commit_count": 50,
                "commit_omission_reason": "First 100 commits retained.",
            }
        )
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
        self.assertEqual(processed.omitted_commit_count, 50)
        self.assertEqual(
            processed.commit_omission_reason, "First 100 commits retained."
        )
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

    def test_projection_bounds_commit_facts_and_records_exact_omission(self):
        payload = {
            "repository": {"id": 6001},
            "commits": [{"id": str(index), "message": "RET-1"} for index in range(150)],
        }
        excerpt = self.repository._redacted_github_payload_excerpt(payload, "push")
        retained = json.loads(excerpt)
        self.assertEqual(len(retained["commits"]), 100)
        self.assertEqual(retained["omitted_commit_count"], 50)
        self.assertEqual(
            [item["id"] for item in retained["commits"]],
            [str(index) for index in range(100)],
        )
        self.assertEqual(
            retained["commits"][0]["message"],
            {"keys": ["RET-1"], "reason": False, "excerpt": "RET-1"},
        )

    def test_projection_bounds_scalars_and_semantic_key_evidence(self):
        keys = ["RET-" + str(index) for index in range(1, 21)]
        payload = {
            "repository": {"id": 6001},
            "ref": "x" * 4096,
            "after": "a" * 128,
            "head_commit": {"timestamp": "t" * 64},
            "commits": [{"id": "a" * 128, "message": " ".join(keys + keys)}],
        }
        retained = json.loads(
            self.repository._redacted_github_payload_excerpt(payload, "push")
        )
        self.assertEqual(retained["commits"][0]["message"]["keys"], keys)
        for field, value in (("ref", "x" * 4097), ("after", "a" * 129)):
            with self.subTest(field=field):
                self.assertFalse(
                    self.repository._redacted_github_payload_excerpt(
                        {**payload, field: value}, "push"
                    )
                )
        payload["commits"][0]["message"] = "RET-" + "1" * 125
        self.assertFalse(
            self.repository._redacted_github_payload_excerpt(payload, "push")
        )
        payload["commits"][0]["message"] = "RET-" + "1" * 124
        self.assertTrue(
            self.repository._redacted_github_payload_excerpt(payload, "push")
        )
        payload["head_commit"]["timestamp"] += "t"
        self.assertFalse(
            self.repository._redacted_github_payload_excerpt(payload, "push")
        )

    def test_maximal_projection_has_a_finite_derived_json_size(self):
        keys = ["AA-1" + f"{index:02d}" + "0" * 122 for index in range(1, 21)]
        commit = {
            "id": "🙂" * 128,
            "timestamp": "🙂" * 64,
            "message": "🙂" * 255 + " " + " ".join(keys),
        }
        payload = {
            "repository": {"id": "🙂" * 128},
            "ref": "🙂" * 4096,
            "after": "🙂" * 128,
            "head_commit": {"timestamp": "🙂" * 64},
            "commits": [commit] * 2048,
        }
        excerpt = self.repository._redacted_github_payload_excerpt(payload, "push")
        self.assertTrue(excerpt)
        self.assertLess(len(excerpt), 900000)
        retained = json.loads(excerpt)
        self.assertEqual(retained["omitted_commit_count"], 1948)
        self.assertEqual(len(retained["commits"]), 100)
        self.assertEqual(retained["commits"][0]["message"]["keys"], keys)
        payload["commits"].append(commit)
        self.assertFalse(
            self.repository._redacted_github_payload_excerpt(payload, "push")
        )

    def test_projection_rejects_malformed_nested_inputs_without_retaining_them(self):
        for event, extra in (
            ("push", {"commits": [{"message": {"secret": "private"}}]}),
            ("push", {"commits": "not-a-list"}),
            (
                "push",
                {
                    "commits": [
                        {
                            "message": {
                                "keys": ["RET-1"],
                                "reason": False,
                                "excerpt": "RET-1",
                            }
                        }
                    ]
                },
            ),
            (
                "pull_request",
                {"pull_request": {"body": {"keys": ["RET-1"], "reason": False}}},
            ),
            ("pull_request", {"pull_request": {"head": []}}),
            ("check_run", {"check_run": {"output": {"title": ["private"]}}}),
        ):
            with self.subTest(event=event, extra=extra):
                self.assertFalse(
                    self.repository._redacted_github_payload_excerpt(
                        {"repository": {"id": 6001}, **extra}, event
                    )
                )

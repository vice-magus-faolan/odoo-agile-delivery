"""Runtime coverage for native leased GitHub fact normalization."""

import json
from uuid import uuid4
from unittest.mock import patch

from odoo import SUPERUSER_ID, api
from odoo.exceptions import AccessError, ValidationError
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

    def _check_run(self, name, output, provider_check_id=3001, updated_at="2026-01-02T03:04:05Z"):
        """Return a complete GitHub check-run payload with caller-controlled ordering and keys."""

        return {
            "repository": {"id": 2001},
            "check_run": {
                "id": provider_check_id,
                "name": name,
                "status": "completed",
                "conclusion": "success",
                "head_sha": "k" * 40,
                "html_url": "https://example.invalid/check/" + str(provider_check_id),
                "completed_at": updated_at,
                "updated_at": updated_at,
                "output": output,
            },
        }

    def _pull_request(self, title, updated_at):
        """Return a complete pull-request payload with caller-controlled title ordering."""

        return {
            "repository": {"id": 2001},
            "number": 4,
            "pull_request": {
                "id": 404,
                "title": title,
                "body": "",
                "state": "open",
                "merged": False,
                "head": {"ref": "feature/no-key", "sha": "p" * 40},
                "base": {"ref": "main"},
                "html_url": "https://example.invalid/pr/4",
                "updated_at": updated_at,
                "merged_at": None,
            },
        }

    def _create_committed_delivery(self):
        """Create one queued delivery visible to independent normalizer transactions."""

        unique_key = uuid4().hex[:8].upper()
        with self.registry._db.cursor() as cursor:
            environment = api.Environment(cursor, SUPERUSER_ID, {})
            project = environment["project.project"].create(
                {
                    "name": "Concurrent normalizer " + unique_key,
                    "privacy_visibility": "employees",
                    "agile_enabled": True,
                    "agile_key": "CN" + unique_key,
                }
            )
            task = environment["project.task"].create(
                {"name": "Concurrent task", "project_id": project.id}
            )
            repository = environment["project.git.repository"].create(
                {
                    "name": "concurrent-" + unique_key.lower(),
                    "provider": "github",
                    "provider_repository_id": "concurrent-" + unique_key,
                    "canonical_url": "https://example.invalid/acme/concurrent-" + unique_key.lower(),
                    "project_id": project.id,
                    "webhook_secret": "fixture-secret",
                    "retention_policy": "redacted_excerpt",
                }
            )
            delivery = environment["project.git.delivery"].create(
                {
                    "repository_id": repository.id,
                    "provider_delivery_id": "delivery-concurrent-" + unique_key,
                    "event_type": "push",
                    "payload_sha256": "c" * 64,
                    "payload_size": 1,
                    "retained_payload": json.dumps(
                        {
                            "repository": {"id": repository.provider_repository_id},
                            "ref": "refs/heads/feature/" + task.agile_key,
                            "after": "c" * 40,
                            "head_commit": {"timestamp": "2026-01-02T03:04:05Z"},
                            "commits": [
                                {
                                    "id": "c" * 40,
                                    "message": task.agile_key,
                                    "timestamp": "2026-01-02T03:04:05Z",
                                    "url": "https://example.invalid/commit/" + ("c" * 40),
                                }
                            ],
                        }
                    ),
                    "state": "queued",
                }
            )
            cursor.commit()
        return {"delivery_id": delivery.id, "repository_id": repository.id}

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

    def test_check_run_creates_fact_and_exact_key_association(self):
        delivery = self._delivery(
            "check_run", self._check_run("CI for NRM-1", {"title": "Build passed"}), "check-run"
        )

        self._process(delivery)

        check = self.env["project.git.check"].search(
            [("repository_id", "=", self.repository.id), ("provider_check_id", "=", "3001")]
        )
        association = self.env["project.git.task.association"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("task_id", "=", self.first_task.id),
                ("source_type", "=", "check"),
                ("source_provider_id", "=", "3001"),
            ]
        )
        audit = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "=", delivery.id),
                ("source_type", "=", "check"),
                ("source_provider_id", "=", "3001"),
                ("source_field", "=", "name"),
                ("agile_key", "=", self.first_task.agile_key),
            ]
        )
        self.assertEqual(delivery.state, "processed")
        self.assertEqual((check.name, check.state, check.ordering_state), ("CI for NRM-1", "success", "known"))
        self.assertEqual((association.agile_key, audit.outcome, audit.reason), ("NRM-1", "associated", "exact_key"))

    def test_stale_and_ambiguous_pull_request_deliveries_keep_own_key_provenance(self):
        newer = self._delivery(
            "pull_request", self._pull_request("NRM-1 current", "2026-01-03T03:04:05Z"), "pr-newer"
        )
        stale = self._delivery(
            "pull_request", self._pull_request("NRM-2 stale", "2026-01-01T03:04:05Z"), "pr-stale"
        )
        ambiguous = self._delivery(
            "pull_request", self._pull_request("NRM-2 equal", "2026-01-03T03:04:05Z"), "pr-ambiguous"
        )

        self._process(newer)
        self._process(stale)
        self._process(ambiguous)

        pull = self.env["project.git.pull.request"].search(
            [("repository_id", "=", self.repository.id), ("provider_request_id", "=", "404")]
        )
        association = self.env["project.git.task.association"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("task_id", "=", self.second_task.id),
                ("source_type", "=", "pull_request"),
                ("source_provider_id", "=", "404"),
            ]
        )
        delivery_audits = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "in", [stale.id, ambiguous.id]),
                ("source_type", "=", "pull_request"),
                ("source_provider_id", "=", "404"),
                ("source_field", "=", "title"),
                ("agile_key", "=", self.second_task.agile_key),
            ]
        )
        leaked_audits = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "in", [stale.id, ambiguous.id]),
                ("source_type", "=", "pull_request"),
                ("source_provider_id", "=", "404"),
                ("source_field", "=", "title"),
                ("agile_key", "=", self.first_task.agile_key),
            ]
        )
        self.assertEqual((pull.title, pull.ordering_state), ("NRM-1 current", "ambiguous"))
        self.assertEqual(association.agile_key, self.second_task.agile_key)
        self.assertEqual(len(delivery_audits), 2)
        self.assertFalse(leaked_audits)

    def test_stale_and_ambiguous_check_deliveries_keep_own_key_provenance(self):
        newer = self._delivery(
            "check_run",
            self._check_run("NRM-1 current", {}, 3002, "2026-01-03T03:04:05Z"),
            "check-newer",
        )
        stale = self._delivery(
            "check_run",
            self._check_run("NRM-2 stale", {}, 3002, "2026-01-01T03:04:05Z"),
            "check-stale",
        )
        ambiguous = self._delivery(
            "check_run",
            self._check_run("NRM-2 equal", {}, 3002, "2026-01-03T03:04:05Z"),
            "check-ambiguous",
        )

        self._process(newer)
        self._process(stale)
        self._process(ambiguous)

        check = self.env["project.git.check"].search(
            [("repository_id", "=", self.repository.id), ("provider_check_id", "=", "3002")]
        )
        association = self.env["project.git.task.association"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("task_id", "=", self.second_task.id),
                ("source_type", "=", "check"),
                ("source_provider_id", "=", "3002"),
            ]
        )
        delivery_audits = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "in", [stale.id, ambiguous.id]),
                ("source_type", "=", "check"),
                ("source_provider_id", "=", "3002"),
                ("source_field", "=", "name"),
                ("agile_key", "=", self.second_task.agile_key),
            ]
        )
        leaked_audits = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "in", [stale.id, ambiguous.id]),
                ("source_type", "=", "check"),
                ("source_provider_id", "=", "3002"),
                ("source_field", "=", "name"),
                ("agile_key", "=", self.first_task.agile_key),
            ]
        )
        self.assertEqual((check.name, check.ordering_state), ("NRM-1 current", "ambiguous"))
        self.assertEqual(association.agile_key, self.second_task.agile_key)
        self.assertEqual(len(delivery_audits), 2)
        self.assertFalse(leaked_audits)

    def test_same_sha_push_deliveries_keep_own_commit_key_provenance(self):
        sha = "r" * 40
        first = self._delivery(
            "push", self._push(sha, "2026-01-02T03:04:05Z", "NRM-1 first"), "commit-first"
        )
        second = self._delivery(
            "push", self._push(sha, "2026-01-03T03:04:05Z", "NRM-2 second"), "commit-second"
        )

        self._process(first)
        self._process(second)

        commit = self.env["project.git.commit"].search(
            [("repository_id", "=", self.repository.id), ("sha", "=", sha)]
        )
        first_association = self.env["project.git.task.association"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("task_id", "=", self.first_task.id),
                ("source_type", "=", "commit"),
                ("source_provider_id", "=", sha),
            ]
        )
        second_association = self.env["project.git.task.association"].search(
            [
                ("repository_id", "=", self.repository.id),
                ("task_id", "=", self.second_task.id),
                ("source_type", "=", "commit"),
                ("source_provider_id", "=", sha),
            ]
        )
        first_audit = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "=", first.id),
                ("source_type", "=", "commit"),
                ("source_provider_id", "=", sha),
                ("source_field", "=", "message"),
                ("agile_key", "=", self.first_task.agile_key),
            ]
        )
        second_audit = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "=", second.id),
                ("source_type", "=", "commit"),
                ("source_provider_id", "=", sha),
                ("source_field", "=", "message"),
                ("agile_key", "=", self.second_task.agile_key),
            ]
        )
        leaked_second_audit = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "=", second.id),
                ("source_type", "=", "commit"),
                ("source_provider_id", "=", sha),
                ("source_field", "=", "message"),
                ("agile_key", "=", self.first_task.agile_key),
            ]
        )
        self.assertEqual(commit.message_excerpt, "NRM-1 first")
        self.assertEqual(first_association.agile_key, self.first_task.agile_key)
        self.assertEqual(second_association.agile_key, self.second_task.agile_key)
        self.assertEqual((first_audit.outcome, first_audit.reason), ("associated", "exact_key"))
        self.assertEqual((second_audit.outcome, second_audit.reason), ("associated", "exact_key"))
        self.assertFalse(leaked_second_audit)

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

    def test_normalizer_claims_a_delivery_only_once(self):
        """Verify a second transaction skips the first worker's held lease lock."""

        fixture = self._create_committed_delivery()
        with self.registry._db.cursor() as first_cursor, self.registry._db.cursor() as second_cursor:
            first_environment = api.Environment(first_cursor, SUPERUSER_ID, {})
            second_environment = api.Environment(second_cursor, SUPERUSER_ID, {})
            first_claim = first_environment["project.git.delivery"]._claim_github_delivery()
            second_claim = second_environment["project.git.delivery"]._claim_github_delivery()

            self.assertEqual(first_claim.id, fixture["delivery_id"])
            self.assertFalse(second_claim)
            self.assertEqual((first_claim.state, first_claim.attempt_count), ("processing", 1))
            self.assertTrue(first_claim.lease_token)

    def test_expired_normalizer_lease_is_recovered_and_settled(self):
        delivery = self._delivery(
            "push", self._push("g" * 40, "2026-01-03T03:04:05Z", "NRM-1 recovered"), "expired"
        )
        delivery.write(
            {
                "state": "processing",
                "lease_token": "expired-token",
                "lease_expires_at": "2000-01-01 00:00:00",
            }
        )

        self._process(delivery)

        self.assertEqual((delivery.state, delivery.attempt_count), ("processed", 1))
        self.assertFalse(delivery.lease_token)

    def test_archived_exact_key_is_audited_without_association(self):
        self.first_task.active = False
        delivery = self._delivery(
            "push", self._push("h" * 40, "2026-01-03T03:04:05Z", self.first_task.agile_key), "archived"
        )

        self._process(delivery)

        associations = self.env["project.git.task.association"].search(
            [("repository_id", "=", self.repository.id), ("task_id", "=", self.first_task.id)]
        )
        audit = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "=", delivery.id),
                ("agile_key", "=", self.first_task.agile_key),
                ("source_type", "=", "commit"),
            ]
        )
        self.assertFalse(associations)
        self.assertEqual((audit.outcome, audit.reason), ("rejected", "archived_task"))
        self.assertFalse(audit.task_id)

    def test_cross_company_wrong_project_key_is_rejected_without_association(self):
        other_company = self.env["res.company"].create({"name": "Other normalizer company"})
        other_project = self.env["project.project"].with_company(other_company).create(
            {
                "name": "Other normalizer project",
                "company_id": other_company.id,
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "OTH",
            }
        )
        other_task = self.env["project.task"].with_company(other_company).create(
            {"name": "Other task", "project_id": other_project.id}
        )
        delivery = self._delivery(
            "push", self._push("i" * 40, "2026-01-03T03:04:05Z", other_task.agile_key), "wrong-project"
        )

        self._process(delivery)

        self.assertFalse(
            self.env["project.git.task.association"].search(
                [("repository_id", "=", self.repository.id), ("task_id", "=", other_task.id)]
            )
        )
        audit = self.env["project.git.association.audit"].search(
            [
                ("delivery_id", "=", delivery.id),
                ("agile_key", "=", other_task.agile_key),
                ("source_type", "=", "commit"),
            ]
        )
        self.assertEqual((audit.outcome, audit.reason), ("rejected", "wrong_project"))
        self.assertFalse(audit.task_id)

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

    def test_falsy_malformed_push_commits_dead_letters_without_fact_writes(self):
        payload = self._push("l" * 40, "2026-01-03T03:04:05Z", self.first_task.agile_key)
        payload["commits"] = ""
        delivery = self._delivery("push", payload, "malformed-commits")

        self._process(delivery)

        self.assertEqual(delivery.state, "failed")
        self.assertIn("commits collection", delivery.error_summary)
        self.assertFalse(self.env["project.git.branch"].search([("repository_id", "=", self.repository.id)]))
        self.assertFalse(self.env["project.git.commit"].search([("repository_id", "=", self.repository.id)]))
        self.assertFalse(
            self.env["project.git.task.association"].search([("repository_id", "=", self.repository.id)])
        )

    def test_falsy_malformed_check_output_dead_letters_without_fact_writes(self):
        delivery = self._delivery(
            "check_run", self._check_run(self.first_task.agile_key, []), "malformed-check-output"
        )

        self._process(delivery)

        self.assertEqual(delivery.state, "failed")
        self.assertIn("check output", delivery.error_summary)
        self.assertFalse(self.env["project.git.check"].search([("repository_id", "=", self.repository.id)]))
        self.assertFalse(
            self.env["project.git.task.association"].search([("repository_id", "=", self.repository.id)])
        )

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

    def test_reprocess_rejects_retryable_and_authorizes_terminal_replay_idempotently(self):
        manager = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "GitHub delivery manager",
                "login": "github-delivery-manager@example.invalid",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "group_ids": [(4, self.env.ref("project.group_project_manager").id)],
            }
        )
        ordinary_user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "GitHub delivery ordinary user",
                "login": "github-delivery-user@example.invalid",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "group_ids": [(4, self.env.ref("base.group_user").id)],
            }
        )
        delivery = self._delivery(
            "push", self._push("j" * 40, "2026-01-03T03:04:05Z", self.first_task.agile_key), "reprocess"
        )
        delivery.state = "retryable"

        with self.assertRaises(ValidationError):
            delivery.with_user(manager).action_reprocess_github_delivery()
        with self.assertRaises(AccessError):
            delivery.with_user(ordinary_user).action_reprocess_github_delivery()

        delivery.state = "failed"
        delivery.with_user(manager).action_reprocess_github_delivery()
        self.assertEqual(delivery.state, "queued")
        with self.assertRaises(ValidationError):
            delivery.with_user(manager).action_reprocess_github_delivery()
        self._process(delivery)

        self.assertEqual(delivery.state, "processed")
        self.assertEqual(
            self.env["project.git.commit"].search_count(
                [("repository_id", "=", self.repository.id), ("sha", "=", "j" * 40)]
            ),
            1,
        )
        self.assertEqual(
            self.env["project.git.task.association"].search_count(
                [
                    ("repository_id", "=", self.repository.id),
                    ("task_id", "=", self.first_task.id),
                    ("source_type", "=", "commit"),
                    ("source_provider_id", "=", "j" * 40),
                ]
            ),
            1,
        )

    def test_unsupported_event_is_terminally_discarded(self):
        delivery = self._delivery("star", {"repository": {"id": 2001}}, "unsupported")

        self._process(delivery)

        self.assertEqual(delivery.state, "discarded")
        self.assertEqual(delivery.error_summary, "Unsupported GitHub event type.")

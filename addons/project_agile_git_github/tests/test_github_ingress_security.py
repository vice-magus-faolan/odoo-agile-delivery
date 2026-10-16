"""Security and database-invariant coverage for GitHub delivery ingress."""

import threading
from unittest.mock import patch
from uuid import uuid4

from psycopg2 import IntegrityError

from odoo import SUPERUSER_ID, api
from odoo.exceptions import AccessError
from odoo.service.model import get_public_method, retrying
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestGitHubIngressSecurity(TransactionCase):
    """Keep protected delivery writes and company boundaries server-side."""

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Ingress security",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "SEC",
            }
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "security",
                "provider": "github",
                "provider_repository_id": "9001",
                "canonical_url": "https://github.com/acme/security",
                "project_id": self.project.id,
                "webhook_secret": "fixture-secret",
            }
        )

    def _delivery_values(self):
        return {
            "repository_id": self.repository.id,
            "provider_delivery_id": "concurrent-delivery",
            "event_type": "push",
            "payload_sha256": "a" * 64,
            "payload_size": 2,
        }

    def test_project_manager_cannot_forge_a_delivery(self):
        manager = mail_new_test_user(
            self.env, "Git delivery manager", groups="project.group_project_manager"
        )

        with self.assertRaises(AccessError):
            self.env["project.git.delivery"].with_user(manager).create(
                self._delivery_values()
            )

    def test_authenticated_recorder_is_idempotent_against_the_database_constraint(self):
        delivery_model = self.env["project.git.delivery"]
        first, first_created = delivery_model._record_authenticated_github_delivery(
            **self._delivery_values()
        )
        replay, replay_created = delivery_model._record_authenticated_github_delivery(
            **self._delivery_values()
        )

        self.assertTrue(first_created)
        self.assertFalse(replay_created)
        self.assertEqual(first, replay)
        self.assertEqual(
            delivery_model.search_count(
                [
                    ("repository_id", "=", self.repository.id),
                    ("provider_delivery_id", "=", "concurrent-delivery"),
                ]
            ),
            1,
        )

    def test_failed_persistence_rolls_back_without_masking_the_failure(self):
        invalid_values = {**self._delivery_values(), "repository_id": 999999}

        with self.assertRaises(IntegrityError):
            self.env["project.git.delivery"]._record_authenticated_github_delivery(
                **invalid_values
            )

        delivery, created = self.env[
            "project.git.delivery"
        ]._record_authenticated_github_delivery(**self._delivery_values())
        self.assertTrue(created)
        self.assertTrue(delivery)

    def test_ingress_lookup_is_private_and_ignores_hostile_company_context(self):
        model = (
            self.env["project.git.repository"]
            .with_user(self.env.ref("base.public_user"))
            .with_context(allowed_company_ids=[999999], active_test=False)
        )
        with self.assertRaises(AccessError):
            get_public_method(model, "_github_ingress_configuration")
        self.assertEqual(
            model._github_ingress_configuration("9001"),
            {
                "id": self.repository.id,
                "webhook_secret": "fixture-secret",
                "retention_policy": "digest_only",
            },
        )
        self.repository.active = False
        self.env["project.git.repository"].create(
            {
                "name": "Different provider",
                "provider": "gitlab",
                "provider_repository_id": "9001",
                "canonical_url": "https://gitlab.com/acme/security",
                "project_id": self.project.id,
                "webhook_secret": "different-secret",
            }
        )
        self.assertIsNone(model._github_ingress_configuration("9001"))
        self.assertIsNone(model._github_ingress_configuration("unknown"))

    def test_replay_mismatches_are_bounded_and_preserve_original_evidence(self):
        model = self.env["project.git.delivery"]
        values = self._delivery_values()
        delivery, _created = model._record_authenticated_github_delivery(**values)
        evidence_fields = [
            "repository_id",
            "provider_delivery_id",
            "event_type",
            "payload_sha256",
            "payload_size",
            "state",
            "received_at",
            "retained_payload",
        ]
        before = delivery.read(evidence_fields)
        delivery.replay_mismatch_count = 99
        fenced = "git_policy_evidence_version" in self.repository._fields
        evidence_version = self.repository.git_policy_evidence_version if fenced else 0
        for changed in (
            {"event_type": "pull_request"},
            {"payload_sha256": "b" * 64},
            {"payload_size": values["payload_size"] + 1},
        ):
            with self.subTest(changed=changed):
                replay, created, exact = model._record_authenticated_github_delivery(
                    **{**values, **changed}, return_replay_status=True
                )
                self.assertEqual(replay, delivery)
                self.assertFalse(created)
                self.assertFalse(exact)
                self.assertEqual(delivery.replay_mismatch_count, 100)
                self.assertTrue(delivery.last_replay_mismatch_at)
                self.assertEqual(delivery.read(evidence_fields), before)
        if fenced:
            self.assertGreater(
                self.repository.git_policy_evidence_version, evidence_version
            )

    def test_failed_replay_write_rolls_back_diagnostics_and_evidence_fence(self):
        model = self.env["project.git.delivery"]
        values = self._delivery_values()
        delivery, _created = model._record_authenticated_github_delivery(**values)
        self.env.flush_all()
        fields = ["replay_mismatch_count", "last_replay_mismatch_at", "payload_sha256"]
        before = delivery.read(fields)
        fenced = "git_policy_evidence_version" in self.repository._fields
        evidence_version = self.repository.git_policy_evidence_version if fenced else 0
        original_write = type(model).write

        def failed_write(records, vals):
            original_write(records, vals)
            records.flush_recordset()
            raise RuntimeError("replay persistence failed")

        with (
            self.assertRaisesRegex(RuntimeError, "replay persistence failed"),
            self.env.cr.savepoint(),
            patch.object(type(model), "write", failed_write),
        ):
            model._record_authenticated_github_delivery(
                **{**values, "payload_sha256": "b" * 64}
            )
        self.assertEqual(delivery.read(fields), before)
        if fenced:
            self.assertEqual(
                self.repository.git_policy_evidence_version, evidence_version
            )


@tagged("post_install", "-at_install")
class TestGitHubIngressReplayConcurrency(TransactionCase):
    """Exercise native transaction retries after registry installation completes."""

    def _remove_committed_replay(self, project_id, repository_id):
        with self.registry._db.cursor() as cursor:
            environment = api.Environment(cursor, SUPERUSER_ID, {})
            repository = environment["project.git.repository"].browse(repository_id)
            repository.git_delivery_ids.unlink()
            repository.unlink()
            environment["project.project"].browse(project_id).unlink()
            cursor.commit()

    def test_competing_authenticated_replays_do_not_lose_mismatch_increments(self):
        """Real sessions retry stale snapshots through the native request contract."""
        unique_key = uuid4().hex[:8].upper()
        with self.registry._db.cursor() as cursor:
            environment = api.Environment(cursor, SUPERUSER_ID, {})
            project = environment["project.project"].create(
                {
                    "name": "Concurrent replay " + unique_key,
                    "privacy_visibility": "employees",
                    "agile_enabled": True,
                    "agile_key": "CR" + unique_key,
                }
            )
            repository = environment["project.git.repository"].create(
                {
                    "name": "Concurrent replay",
                    "provider": "github",
                    "provider_repository_id": "replay-" + unique_key,
                    "canonical_url": "https://github.com/acme/replay",
                    "project_id": project.id,
                }
            )
            values = {
                "repository_id": repository.id,
                "provider_delivery_id": "concurrent-delivery",
                "event_type": "push",
                "payload_sha256": "a" * 64,
                "payload_size": 2,
            }
            delivery, _created = environment[
                "project.git.delivery"
            ]._record_authenticated_github_delivery(**values)
            delivery_id = delivery.id
            cursor.commit()
        self.addCleanup(self._remove_committed_replay, project.id, repository.id)
        ready = threading.Barrier(2)
        results, failures = [], []

        def record_replay(environment):
            try:
                cursor = environment.cr
                # Both transactions start from the same pre-increment snapshot.
                self.assertEqual(
                    environment["project.git.delivery"]
                    .browse(delivery_id)
                    .replay_mismatch_count,
                    0,
                )
                ready.wait(timeout=5)

                def record():
                    cursor.execute("SET LOCAL lock_timeout = %s", ("3s",))
                    cursor.execute("SET LOCAL statement_timeout = %s", ("10s",))
                    replay, created, exact = environment[
                        "project.git.delivery"
                    ]._record_authenticated_github_delivery(
                        **{**values, "payload_sha256": "b" * 64},
                        return_replay_status=True,
                    )
                    return replay.id, created, exact

                results.append(retrying(record, environment))
            except BaseException as error:  # pragma: no cover - asserted below
                failures.append(error)

        with (
            self.registry._db.cursor() as first_cursor,
            self.registry._db.cursor() as second_cursor,
        ):
            environments = [
                api.Environment(cursor, SUPERUSER_ID, {})
                for cursor in (first_cursor, second_cursor)
            ]
            threads = [
                threading.Thread(target=record_replay, args=(environment,))
                for environment in environments
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(60)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertFalse(failures, failures)
            self.assertEqual(results, [(delivery_id, False, False)] * 2)
        with self.registry._db.cursor() as cursor:
            environment = api.Environment(cursor, SUPERUSER_ID, {})
            deliveries = environment["project.git.delivery"].search(
                [("repository_id", "=", repository.id)]
            )
            self.assertEqual(deliveries.ids, [delivery_id])
            self.assertEqual(deliveries.replay_mismatch_count, 2)
            self.assertTrue(deliveries.last_replay_mismatch_at)
            self.assertEqual(deliveries.payload_sha256, values["payload_sha256"])

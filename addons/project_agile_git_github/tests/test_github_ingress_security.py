"""Security and database-invariant coverage for GitHub delivery ingress."""

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
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

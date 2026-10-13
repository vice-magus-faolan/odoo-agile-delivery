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

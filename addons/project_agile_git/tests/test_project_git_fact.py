"""Runtime regression tests for the small provider-neutral Git facts skeleton."""

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProjectGitFact(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Engineering",
                "privacy_visibility": "employees",
                "agile_enabled": True,
                "agile_key": "ENG",
            }
        )
        self.task = self.env["project.task"].create(
            {"name": "Immutable association", "project_id": self.project.id}
        )
        self.repository = self.env["project.git.repository"].create(
            {
                "name": "delivery",
                "provider": "github",
                "provider_repository_id": "42",
                "canonical_url": "https://github.com/acme/delivery",
                "project_id": self.project.id,
            }
        )

    def test_repository_requires_an_agile_project(self):
        ordinary_project = self.env["project.project"].create(
            {"name": "Ordinary", "privacy_visibility": "employees"}
        )

        with self.assertRaises(ValidationError):
            self.env["project.git.repository"].create(
                {
                    "name": "ordinary",
                    "provider": "github",
                    "provider_repository_id": "43",
                    "canonical_url": "https://github.com/acme/ordinary",
                    "project_id": ordinary_project.id,
                }
            )

    def test_delivery_identity_is_repository_scoped(self):
        values = {
            "repository_id": self.repository.id,
            "provider_delivery_id": "delivery-1",
            "event_type": "push",
            "payload_sha256": "a" * 64,
            "payload_size": 2,
        }
        delivery = self.env["project.git.delivery"].create(values)

        self.assertEqual(delivery.state, "received")
        with self.env.cr.savepoint(), self.assertRaises(IntegrityError):
            self.env["project.git.delivery"].create(values)

    def test_task_association_captures_the_immutable_agile_key(self):
        association = self.env["project.git.task.association"].create(
            {
                "repository_id": self.repository.id,
                "task_id": self.task.id,
                "source_type": "pull_request",
                "source_provider_id": "99",
            }
        )

        self.assertEqual(association.agile_key, self.task.agile_key)
        with self.assertRaises(ValidationError):
            association.write({"source_provider_id": "100"})
        with self.assertRaises(ValidationError):
            association.unlink()

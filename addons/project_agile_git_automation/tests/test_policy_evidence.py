"""Executable regression for canonical Git policy evidence."""

import hashlib

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.project_agile_git_automation.models.policy_evidence import (
    FULL_SHA,
    canonical,
    fingerprint,
    reduce_conditions,
)


@tagged("post_install", "-at_install")
class TestGitPolicyEvidence(TransactionCase):
    def test_versioned_evidence_golden_serialization_and_failure_precedence(self):
        evidence = {"version": 1, "task": {"stage": 2, "key": "ENG-1"}, "checks": []}
        golden = b'{"checks":[],"task":{"key":"ENG-1","stage":2},"version":1}'
        self.assertEqual(canonical(evidence).encode(), golden)
        self.assertEqual(fingerprint(evidence), hashlib.sha256(golden).hexdigest())
        self.assertEqual(
            reduce_conditions(
                [("waiting", "missing_check"), ("rejected", "check_failed")]
            ),
            ("rejected", "check_failed"),
        )
        for size in (40, 64):
            self.assertIsNotNone(FULL_SHA.fullmatch("A" * size))
        for value in ("a" * 39, "a" * 41, " a" * 20, "a" * 40 + "\n", "g" * 40):
            self.assertIsNone(FULL_SHA.fullmatch(value))

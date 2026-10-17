"""Executable regression for canonical Git policy evidence."""

import hashlib
import importlib.util
import unittest
from pathlib import Path


class TestGitAutomationContract(unittest.TestCase):
    # Plain unittest.TestCase has no Odoo transaction setup to chain.
    def setUp(self):  # pylint: disable=method-required-super
        self.root = Path(__file__).resolve().parents[1]
        self.addon = self.root / "addons" / "project_agile_git_automation"

    def test_versioned_evidence_golden_serialization_and_failure_precedence(self):
        path = self.addon / "models" / "policy_evidence.py"
        spec = importlib.util.spec_from_file_location("policy_evidence", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        evidence = {"version": 1, "task": {"stage": 2, "key": "ENG-1"}, "checks": []}
        golden = b'{"checks":[],"task":{"key":"ENG-1","stage":2},"version":1}'
        self.assertEqual(module.canonical(evidence).encode(), golden)
        self.assertEqual(
            module.fingerprint(evidence), hashlib.sha256(golden).hexdigest()
        )
        self.assertEqual(
            module.reduce_conditions(
                [("waiting", "missing_check"), ("rejected", "check_failed")]
            ),
            ("rejected", "check_failed"),
        )
        for size in (40, 64):
            self.assertIsNotNone(module.FULL_SHA.fullmatch("A" * size))
        for value in ("a" * 39, "a" * 41, " a" * 20, "a" * 40 + "\n", "g" * 40):
            self.assertIsNone(module.FULL_SHA.fullmatch(value))


if __name__ == "__main__":
    unittest.main()

"""Regression checks for the safe Milestone 3 verification workflow."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class TestVerifyContract(unittest.TestCase):
    def test_uninstall_reports_logged_errors_and_preserves_command_status(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" / "verify").read_text()
        # Run the production function without the verifier's Docker lifecycle.
        function = script.split("\nuninstall_module() {", 1)[1].split(
            "\nsolution_lifecycle() {", 1
        )[0]
        cases = (
            ("INFO uninstall complete", 0, 0),
            ("ERROR missing policy table during uninstall", 0, 1),
            ("ERROR uninstall command failed", 23, 23),
        )
        for output, command_status, expected_status in cases:
            with self.subTest(output=output, command_status=command_status):
                with tempfile.TemporaryDirectory(prefix="verify-uninstall-") as directory:
                    fixture = Path(directory)
                    producer = fixture / "producer"
                    producer.write_text(
                        'while IFS= read -r line; do :; done\n'
                        'printf "%s\\n" "$UNINSTALL_OUTPUT" >&2\n'
                        'exit "$UNINSTALL_STATUS"\n'
                    )
                    driver = fixture / "driver"
                    driver.write_text(
                        'set -euo pipefail\n'
                        'COMPOSE=(bash "$1")\n'
                        'DATABASE_REINSTALL=disposable_fixture\n'
                        'uninstall_module() {' + function
                        + '\nuninstall_module project_agile_git_automation\n'
                    )
                    result = subprocess.run(
                        ["bash", str(driver), str(producer)],
                        env=dict(os.environ, TMPDIR=directory,
                                 UNINSTALL_OUTPUT=output,
                                 UNINSTALL_STATUS=str(command_status)),
                        capture_output=True, text=True, timeout=10, check=False,
                    )
                    self.assertEqual(result.returncode, expected_status, result.stderr)
                    self.assertIn(output, result.stdout + result.stderr)
                    self.assertEqual(set(fixture.iterdir()), {driver, producer})

    def test_verification_covers_all_modules_and_lifecycles(self):
        root = Path(__file__).resolve().parents[1]
        verify_script = (root / "scripts" / "verify").read_text()
        readme = (root / "README.md").read_text()

        self.assertIn(
            "MODULES=project_agile,project_scrum,project_scrum_analytics,project_agile_ui", verify_script
        )
        self.assertIn(
            "TEST_TAGS=/project_agile,/project_scrum,/project_scrum_analytics,/project_agile_ui",
            verify_script,
        )
        self.assertIn('--update "$MODULES"', verify_script)
        self.assertIn("uninstall_module project_agile_ui", verify_script)
        self.assertIn("uninstall_module project_scrum_analytics", verify_script)
        self.assertIn("uninstall_module project_scrum", verify_script)
        self.assertIn("uninstall_module project_agile", verify_script)
        self.assertNotIn("dropdb -U odoo --if-exists --force", verify_script)
        self.assertIn("VERIFICATION_DATABASES", verify_script)
        self.assertIn("pg_terminate_backend", verify_script)
        self.assertIn("compose.verify.yaml", verify_script)
        self.assertIn(
            "FROM odoo:19.0",
            (root / "Dockerfile.verify").read_text(),
        )
        self.assertIn(
            "websocket-client==1.8.0",
            (root / "Dockerfile.verify").read_text(),
        )
        self.assertIn(
            "google-chrome-stable_154.0.8037.57-1_amd64.deb",
            (root / "Dockerfile.verify").read_text(),
        )
        self.assertIn(
            "66c0645f6a19871bab2844b8537c11a0db2e7d3bea8ef85a1c7cb52a54e65a3e",
            (root / "Dockerfile.verify").read_text(),
        )
        self.assertIn("Milestone 5 planning-board verification boundary", readme)
        self.assertIn("test-only verification image", readme)
        self.assertIn("only its three declared disposable databases", readme)
        self.assertNotIn("Milestone 3 verification boundary", readme)
        self.assertIn("Milestone 5 planning-board verification passed.", verify_script)

    def test_planning_concurrency_harness_is_task_scoped_and_bounded(self):
        root = Path(__file__).resolve().parents[1]
        harness = (root / "scripts" / "test_planning_concurrency.py").read_text()
        worker = (root / "scripts" / "planning_concurrency_worker.py").read_text()

        self.assertIn("odoo_agile_planning_concurrency_t_b1f7013f", harness)
        self.assertIn("lock_timeout", worker)
        self.assertIn("statement_timeout", worker)
        self.assertIn("assign", harness)
        self.assertIn("reorder", harness)

    def test_server_modules_remain_free_of_custom_javascript_assets(self):
        root = Path(__file__).resolve().parents[1] / "addons"
        self.assertFalse((root / "project_scrum" / "static").exists())
        self.assertFalse((root / "project_scrum_analytics" / "static").exists())

    def test_ui_fixture_uses_the_odoo_native_test_asset(self):
        root = Path(__file__).resolve().parents[1] / "addons"
        self.assertTrue(
            (root / "project_agile_ui" / "static" / "tests" / "planning_board_contract.test.js").is_file()
        )

    def test_recovery_documentation_matches_the_lifecycle_guard(self):
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text()
        analytics_readme = (
            root / "addons" / "project_scrum_analytics" / "README.md"
        ).read_text()
        analytics_adr = (root / "docs" / "adrs" / "009-scrum-analytics-semantics.md").read_text()
        scope_adr = (root / "docs" / "adrs" / "003-sprint-scope-history-strategy.md").read_text()

        for document in (readme, analytics_readme, analytics_adr, scope_adr):
            document = " ".join(document.split())
            self.assertIn("Superuser recovery may correct `closed_at`", document)
            self.assertIn("lifecycle state remains action-only", document)

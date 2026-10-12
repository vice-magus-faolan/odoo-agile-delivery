"""Unit checks for discovery gate behavior, not substitute native Odoo proof."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_solution_test_run.py"


class TestSolutionNativeDiscoveryGate(unittest.TestCase):
    def _run(self, text, args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=text,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_zero_baseline_discovery_is_rejected(self):
        result = self._run(
            "Odoo exited successfully but no target tests ran.\n",
            ["--init", "project_agile_solution", "--test-enable"],
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not actually discovered", result.stderr)

    def test_missing_single_test_is_rejected(self):
        methods = self._methods()
        text = "".join(
            f"Starting TestSolutionBaseline.{name}\n" for name in sorted(methods)[1:]
        )
        self.assertNotEqual(
            self._run(
                text, ["--update", "project_agile_solution", "--test-enable"]
            ).returncode,
            0,
        )

    def test_exact_parser_fixture_streams_all_declared_methods(self):
        text = self._complete_stream()
        result = self._run(text, ["--init", "project_agile_solution", "--test-enable"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("M8_BASELINE_NATIVE_DISCOVERY_OK", result.stdout)
        self.assertIn(text, result.stdout)

    def test_other_addons_and_schema_only_setup_do_not_require_tests(self):
        for args in (
            ["--init", "project_agile_solution"],
            ["--init", "project_agile_git_automation", "--test-enable"],
        ):
            self.assertEqual(self._run("Setup only\n", args).returncode, 0)

    def _existing_stream(self):
        classes = {
            "TestSolutionBaseline": "expected_methods",
            "TestSolutionRequirements": "expected_requirement_methods",
            "TestSolutionTaskTrace": "expected_trace_methods",
            "TestSolutionRendering": "expected_rendering_methods",
            "TestSolutionRenderTour": "expected_render_tour_methods",
        }
        return "".join(
            f"Starting {name}.{method}\n"
            for name, function in classes.items()
            for method in sorted(self._methods(function))
        )

    def test_omitted_lineage_suite_cannot_pass_canonical_gate(self):
        result = self._run(
            self._existing_stream(),
            ["--init", "project_agile_solution", "--test-enable"],
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LINEAGE tests not actually discovered", result.stderr)

    def test_starting_tests_is_not_proof_they_passed(self):
        text = (
            self._complete_stream()
            + "1 failed, 0 error(s) of 105 tests when loading database\n"
        )
        result = self._run(text, ["--init", "project_agile_solution", "--test-enable"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("native test failure", result.stderr)

    def _module(self):
        spec = importlib.util.spec_from_file_location("solution_discovery_gate", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _complete_stream(self, addons=("project_agile_solution",)):
        return (
            "".join(
                f"Starting {name}.{method}\n"
                for name, (_, methods) in self._module().declared_suites(addons).items()
                for method in sorted(methods)
            )
            + "0 failed, 0 error(s) of 105 tests when loading database\n"
        )

    def test_bridge_requires_its_own_declared_native_methods(self):
        args = ["--init", "project_agile_solution_scrum", "--test-enable"]
        self.assertNotEqual(self._run(self._complete_stream(), args).returncode, 0)
        text = self._complete_stream(
            ("project_agile_solution", "project_agile_solution_scrum")
        )
        self.assertEqual(self._run(text, args).returncode, 0)

    def test_new_native_suites_are_required_and_unimported_files_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "example" / "tests"
            directory.mkdir(parents=True)
            initializer = directory / "__init__.py"
            initializer.write_text("")
            (directory / "test_new.py").write_text(
                "class TestNew:\n    def test_actual_boundary(self):\n        pass\n"
            )
            with self.assertRaisesRegex(ValueError, "not imported"):
                self._module().declared_suites(("example",), root)
            initializer.write_text("from . import test_new\n")
            suites = self._module().declared_suites(("example",), root)
            self.assertEqual(suites, {"TestNew": ("TestNew", {"test_actual_boundary"})})

    def test_successful_summary_does_not_reject_a_complete_stream(self):
        text = (
            self._complete_stream()
            + "0 failed, 0 error(s) of 105 tests when loading database\n"
        )
        self.assertEqual(
            self._run(
                text, ["--init", "project_agile_solution", "--test-enable"]
            ).returncode,
            0,
        )

    def test_complete_start_lines_without_native_result_are_rejected(self):
        starts = self._complete_stream().split("0 failed,")[0]
        result = self._run(
            starts, ["--init", "project_agile_solution", "--test-enable"]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing successful native result summary", result.stderr)

    def test_empty_result_and_later_success_cannot_mask_missing_or_failed_execution(
        self,
    ):
        args = ["--init", "project_agile_solution", "--test-enable"]
        starts = self._complete_stream().split("0 failed,")[0]
        empty = starts + "0 failed, 0 error(s) of 0 tests when loading database\n"
        self.assertNotEqual(self._run(empty, args).returncode, 0)
        failed = (
            "0 failed, 1 error(s) of 105 tests when loading database\n"
            + self._complete_stream()
        )
        self.assertNotEqual(self._run(failed, args).returncode, 0)

    def test_skipped_native_browser_method_is_not_execution_proof(self):
        method = sorted(self._methods("expected_render_tour_methods"))[0]
        for description in (
            f"TestSolutionRenderTour.{method}",
            f'Subtest TestSolutionRenderTour.{method} (method="read")',
        ):
            with self.subTest(description=description):
                text = (
                    self._complete_stream()
                    + f"skipped {description} : browser unavailable\n"
                )
                result = self._run(
                    text, ["--init", "project_agile_solution", "--test-enable"]
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("was skipped", result.stderr)

    def test_missing_requirement_discovery_is_rejected(self):
        text = "".join(
            f"Starting TestSolutionBaseline.{name}\n"
            for name in sorted(self._methods())
        )
        result = self._run(text, ["--init", "project_agile_solution", "--test-enable"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requirement tests not actually discovered", result.stderr)

    def _methods(self, function="expected_methods"):
        methods = getattr(self._module(), function)()
        self.assertTrue(methods)
        return methods

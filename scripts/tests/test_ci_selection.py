"""Exercise selection against real committed source graphs and Git comparisons."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "ci_selection", Path(__file__).resolve().parents[1] / "ci_selection.py"
)
selection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selection)


class SelectionCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory(prefix="ci-selection-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.email", "selector@example.invalid")
        self.git("config", "user.name", "Selector tests")
        self.addon("core", ["project"])
        self.addon("middle", ["core"])
        self.addon("leaf", ["middle"])
        self.addon("other", ["project"])
        self.addon("extension", ["project"])
        self.write(
            "addons/extension/models.py", "from odoo.addons.leaf import models\n"
        )
        self.addon("optional", ["document_page_project", "core"])
        self.base = self.commit()

    def git(self, *args):
        return (
            subprocess.check_output(
                ["git", "-C", str(self.root), *args], stderr=subprocess.PIPE
            )
            .decode()
            .strip()
        )

    def write(self, path, content):  # pylint: disable=method-required-super
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def addon(self, name, depends):
        self.write(
            f"addons/{name}/__manifest__.py",
            repr({"depends": depends, "installable": True}) + "\n",
        )
        self.write(f"addons/{name}/models.py", "VALUE = 1\n")

    def commit(self):
        self.git("add", "--all")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def decision(self):
        return selection.decide(self.root, self.base, self.commit())

    def test_default_complete_supported_suite(self):
        result = selection.decide(self.root)
        self.assertEqual(result["mode"], "full")
        self.assertEqual(
            set(result["selected"]), {"core", "middle", "leaf", "other", "extension"}
        )
        self.assertEqual(result["excluded"], ["optional"])
        self.assertLess(
            result["install"].index("core"), result["install"].index("middle")
        )
        self.assertIn("hr_timesheet", result["install"])

    def test_direct_and_transitive_manifest_and_extension_dependents(self):
        self.write("addons/core/models.py", "VALUE = 2\n")
        result = self.decision()
        self.assertEqual(result["mode"], "selected")
        self.assertEqual(
            set(result["selected"]), {"core", "middle", "leaf", "extension"}
        )
        self.assertIn("other", result["install"])
        self.assertNotIn("other", result["selected"])

    def test_leaf_does_not_test_prerequisites(self):
        self.write("addons/leaf/models.py", "VALUE = 2\n")
        result = self.decision()
        self.assertEqual(result["mode"], "selected")
        self.assertEqual(result["selected"], ["extension", "leaf"])
        self.assertIn("core", result["install"])
        self.assertNotIn("core", result["selected"])

    def test_focused_mode_keeps_dependents(self):
        result = selection.decide(self.root, addons=["leaf"])
        self.assertEqual(result["selected"], ["extension", "leaf"])
        with self.assertRaises(ValueError):
            selection.decide(self.root, addons=["optional"])

    def test_shared_unknown_and_manifest_changes_are_full(self):
        for path in ("scripts/verify", "unknown.file", "addons/core/__manifest__.py"):
            with self.subTest(path=path):
                self.git("reset", "--hard", self.base)
                self.write(
                    path,
                    "# changed\n"
                    + (repr({"depends": ["project"]}) if path.endswith(".py") else ""),
                )
                self.assertEqual(self.decision()["mode"], "full")

    def test_documentation_only_is_explicit(self):
        self.write("docs/contributing.md", "Guide\n")
        self.write("addons/core/readme/CONFIGURE.md", "Guide\n")
        result = self.decision()
        self.assertEqual(result["mode"], "none")
        self.assertEqual(result["selected"], [])
        self.assertIn("documentation only", result["reason"])

    def test_executable_readme_content_is_not_documentation(self):
        self.write("addons/core/readme/check.py", "VALUE = 1\n")
        self.assertEqual(self.decision()["mode"], "selected")

    def test_rename_and_deletion_are_full(self):
        for rename in (False, True):
            with self.subTest(rename=rename):
                self.git("reset", "--hard", self.base)
                if rename:
                    self.git("mv", "addons/other/models.py", "addons/other/renamed.py")
                else:
                    self.git("rm", "addons/other/models.py")
                self.assertEqual(self.decision()["mode"], "full")

    def test_native_portal_dependency_is_supported(self):
        self.addon("customer", ["core", "portal"])
        result = self.decision()
        self.assertIn("customer", result["selected"])
        self.assertNotIn("customer", result["excluded"])

    def test_added_addon_changes_graph(self):
        self.addon("added", ["core"])
        result = self.decision()
        self.assertEqual(result["mode"], "full")
        self.assertIn("added", result["selected"])

    def test_deleted_addon_is_full(self):
        self.git("rm", "-r", "addons/other")
        self.assertEqual(self.decision()["mode"], "full")

    def test_missing_comparison_and_wrong_head_fall_back(self):
        for base, head in (("missing-object", self.base), (self.base, "missing-head")):
            with self.subTest(base=base, head=head):
                result = selection.decide(self.root, base, head)
                self.assertEqual(result["mode"], "full")
                self.assertIn("analysis unavailable", result["reason"])

    def test_comparison_uses_merge_base(self):
        self.write("docs/base.md", "Base branch\n")
        advanced_base = self.commit()
        self.git("checkout", "-q", "--detach", self.base)
        self.write("addons/other/models.py", "VALUE = 2\n")
        head = self.commit()
        result = selection.decide(self.root, advanced_base, head)
        self.assertEqual(result["mode"], "selected")
        self.assertEqual(result["selected"], ["other"])

    def test_merge_checkout_compares_against_advanced_base(self):
        self.write("addons/core/models.py", "VALUE = 2\n")
        advanced_base = self.commit()
        self.git("checkout", "-q", "--detach", self.base)
        self.write("addons/other/models.py", "VALUE = 2\n")
        feature_head = self.commit()
        self.git("checkout", "-q", "--detach", advanced_base)
        self.git("merge", "--no-ff", "-qm", "PR merge", feature_head)
        merged_head = self.git("rev-parse", "HEAD")
        self.assertEqual(self.git("rev-parse", "HEAD^1"), advanced_base)
        self.assertEqual(self.git("rev-parse", "HEAD^2"), feature_head)
        self.assertEqual(self.git("show", "HEAD:addons/core/models.py"), "VALUE = 2")
        result = selection.decide(self.root, advanced_base, merged_head)
        self.assertEqual(result["mode"], "selected")
        self.assertEqual(result["selected"], ["other"])
        self.assertNotIn("analysis unavailable", result["reason"])

    def test_invalid_graph_cannot_be_full_or_empty_green(self):
        for depends in (["missing_dependency"], ["leaf"]):
            with self.subTest(depends=depends):
                self.git("reset", "--hard", self.base)
                self.addon("core", depends)
                self.commit()
                with self.assertRaises(ValueError):
                    selection.decide(self.root, self.base, "HEAD")

    def test_failed_import_analysis_is_full(self):
        self.write("addons/other/models.py", "invalid python !!!\n")
        result = self.decision()
        self.assertEqual(result["mode"], "full")
        self.assertIn("analysis unavailable", result["reason"])


if __name__ == "__main__":
    unittest.main()

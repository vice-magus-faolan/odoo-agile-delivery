"""Structural contract tests for the installable project_agile skeleton."""

import ast
import unittest
from pathlib import Path


class TestProjectAgileModuleContract(unittest.TestCase):
    """Keep the initial module boundary intentionally small and Odoo-native."""

    def test_manifest_declares_only_project_dependency(self):
        module_root = Path(__file__).resolve().parents[1]
        manifest = ast.literal_eval((module_root / "__manifest__.py").read_text())

        self.assertEqual(manifest["depends"], ["project"])
        self.assertEqual(manifest["author"], "McCann Hub")
        self.assertTrue(manifest["installable"])

    def test_skeleton_has_no_custom_javascript(self):
        module_root = Path(__file__).resolve().parents[1]

        self.assertFalse((module_root / "static").exists())

"""Static discovery/metadata checks complement, never substitute, native proof."""
import ast
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'addons/project_agile_solution'


class TestRequirementContextContract(unittest.TestCase):
    def test_concrete_models_are_imported_and_scope_rules_are_global(self):
        imports = (ADDON / 'models/__init__.py').read_text()
        rules = ET.parse(ADDON / 'security/project_agile_solution_rules.xml')
        concrete = {'solution_requirement': ['project.agile.requirement', 'project.agile.requirement.revision'],
                    'solution_context': ['project.agile.solution.context', 'project.agile.solution.context.revision']}
        for module, models in concrete.items():
            self.assertIn('from . import ' + module, imports)
            source = (ADDON / f'models/{module}.py').read_text()
            for model in models:
                self.assertIn("_name = '" + model + "'", source)
                model_id = 'model_' + model.replace('.', '_')
                model_rules = [record for record in rules.findall('record') if any(field.get('ref') == model_id for field in record.findall('field'))]
                self.assertEqual(len(model_rules), 2, model)
                self.assertFalse(any(record.find("field[@name='groups']") is not None for record in model_rules))
        self.assertIn('UNIQUE(project_id, key)', (ADDON / 'models/solution_requirement.py').read_text())
        self.assertIn('UNIQUE(requirement_id, number)', (ADDON / 'models/solution_requirement.py').read_text())
        self.assertIn('UNIQUE(context_id, number)', (ADDON / 'models/solution_context.py').read_text())

    def test_native_requirements_and_canonical_races_are_not_optional_discovery(self):
        self.assertIn('test_solution_requirements', (ADDON / 'tests/__init__.py').read_text())
        gate = (ROOT / 'scripts/check_solution_test_run.py').read_text()
        self.assertIn('M8_REQUIREMENTS_NATIVE_DISCOVERY_OK', gate)
        self.assertIn('missing_requirements', gate)
        self.assertIn('requirement_concurrency', (ROOT / 'scripts/solution_source_probe.py').read_text())
        tree = ast.parse((ADDON / 'tests/test_solution_requirements.py').read_text())
        methods = {node.name for cls in tree.body if isinstance(cls, ast.ClassDef) for node in cls.body if isinstance(node, ast.FunctionDef)}
        for name in ('test_hidden_requirement_context_project_and_spike_read_export_fail_closed',
                     'test_inverse_membership_commands_and_seal_audit_cannot_rewrite_history',
                     'test_three_synthetic_scenarios_create_real_intent_context_and_narrative',
                     'test_native_forms_edit_working_intent_and_explicit_question_resolution'):
            self.assertIn(name, methods)

    def test_editable_skeletons_and_project_specific_fixture_content(self):
        root = ET.parse(ADDON / 'data/solution_templates.xml').getroot()
        self.assertEqual(root.get('noupdate'), '1')
        sow, brief = root.findall('record')
        payload = sow.find("field[@name='sections_json']")
        company = sow.find("field[@name='company_id']")
        kind = brief.find("field[@name='kind']")
        assert payload is not None and payload.text is not None and company is not None and kind is not None
        sections = json.loads(payload.text)
        self.assertEqual(len(sections), 10)
        self.assertIn('Optional commercial references', [row['title'] for row in sections])
        self.assertEqual(company.get('eval'), 'False')
        self.assertEqual(kind.text, 'spec')
        fixtures = json.loads((ADDON / 'tests/fixtures/synthetic_scenarios.json').read_text())
        for scenario in fixtures['scenarios']:
            self.assertTrue(scenario['journey'].startswith('SYNTHETIC'))
            self.assertIn(scenario['questions'][0]['significance'], ('informational', 'planning', 'blocking'))
            if scenario['sow']:
                self.assertEqual(len(scenario['sow_narrative']), len(sections))
                self.assertTrue(all(scenario['sow_narrative']))

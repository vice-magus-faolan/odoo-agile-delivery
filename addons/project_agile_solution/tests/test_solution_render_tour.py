"""Native browser preview/report journeys for all three synthetic narratives."""
import json
import copy
from pathlib import Path

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import HttpCase, tagged

from .solution_fixture import seed_scenario


@tagged('post_install', '-at_install')
class TestSolutionRenderTour(HttpCase):
    def setUp(self):
        super().setUp()
        self.manager = mail_new_test_user(self.env, 'solution_tour_manager', groups='project.group_project_manager')
        self.reader = mail_new_test_user(self.env, 'solution_tour_reader', groups='project.group_project_user,base.group_allow_export')
        self.scenarios = json.loads((Path(__file__).parent / 'fixtures/synthetic_scenarios.json').read_text())['scenarios']

    def test_three_native_form_audience_and_direct_report_browser_journeys(self):
        for scenario in self.scenarios:
            scenario = copy.deepcopy(scenario)
            scenario['requirements'][0]['text'] += ' <img src=x onerror="window.solutionInjected=true">'
            seeded = seed_scenario(self.env, self.manager, self.env.company, scenario)
            # Add explicit private content on a separate working revision;
            # preview must not alias the approved baseline to this newer row.
            draft = seeded['spec'].browse(seeded['spec'].action_new_revision()['res_id'])
            draft.write({'section_ids': [Command.create({'title': 'SECRET TOUR', 'body': '<p>SECRET TOUR narrative</p>'})]})
            action_id = self.env.ref('project_agile_solution.action_solution_revision').id
            self.start_tour(f'/odoo/action-{action_id}/{draft.id}', 'solution_exact_preview', login=self.reader.login)
            report = f'/report/html/project_agile_solution.report_solution_customer/{seeded["spec"].id}'
            self.browser_js(report, """
                if (!document.querySelector('.o_solution_projection')) { throw new Error('Missing native QWeb projection'); }
                if (!document.body.textContent.includes('Redacted customer projection') || document.body.textContent.includes('SECRET TOUR')) {
                    throw new Error('Wrong audience or hidden narrative on direct native report route');
                }
                if (document.body.textContent.includes('Unapproved working')) { throw new Error('Report substituted a moving draft for exact baseline'); }
                if (window.solutionInjected || document.querySelector('.o_solution_projection img[src="x"]')) { throw new Error('Native report executed injected requirement markup'); }
                console.log('test successful');
            """, login=self.reader.login, ready="!!document.querySelector('.o_solution_projection')")

    def test_native_report_http_denies_now_inaccessible_project_and_public(self):
        seeded = seed_scenario(self.env, self.manager, self.env.company, self.scenarios[0])
        baseline = seeded['spec']
        scenario_title = seeded['requirements']['FR1'].title
        url = f'/report/html/project_agile_solution.report_solution_customer/{baseline.id}'
        self.authenticate(self.reader.login, self.reader.login)
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Redacted customer projection', response.text)
        self.env['ir.rule'].create({'name': 'SYNTHETIC report project denial',
            'model_id': self.env['ir.model']._get_id('project.project'), 'domain_force': repr([('id', '!=', seeded['project'].id)])})
        self.env.flush_all()
        denied = self.url_open(url)
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(scenario_title, denied.text)
        self.assertNotIn('Redacted customer projection', denied.text)
        self.authenticate(None, None)
        public = self.url_open(url)
        self.assertNotIn(scenario_title, public.text)

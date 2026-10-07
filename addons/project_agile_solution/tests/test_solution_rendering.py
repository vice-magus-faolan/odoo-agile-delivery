"""Real report/export/authority tests and three explicitly synthetic narratives."""
import json
from pathlib import Path


from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import Form

from .solution_fixture import seed_scenario
from .test_solution_requirements import TestSolutionRequirements


class TestSolutionRendering(TestSolutionRequirements):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager.write({'group_ids': [Command.link(cls.env.ref('base.group_allow_export').id)]})

    def _approved(self, requirement=None, **values):
        requirement = requirement or self._requirement(audience='customer')
        revision = self._revision(requirement_revision_ids=[Command.set(requirement.ids)], **values)
        self._approve(revision)
        return revision, requirement

    def _event(self, baseline, requirement, **values):
        return self.env['project.agile.requirement.acceptance'].with_user(self.manager).create({
            'document_revision_id': baseline.id, 'requirement_revision_id': requirement.id,
            'decision': 'accepted', 'authority_label': 'SYNTHETIC scope owner',
            'criteria_evaluated': requirement.acceptance_expectations,
            'evidence': 'synthetic://evaluation/negative-matrix; asserted test fixture, not production', **values})

    def _html(self, revision, selected_audience='internal', **data):
        reports = self.env['ir.actions.report'].with_user(self.user)
        content, kind = reports._render_qweb_html('project_agile_solution.report_solution_' + selected_audience, revision.ids, data=data)
        self.assertEqual(kind, 'html')
        return content.decode()

    def test_customer_projection_redacts_internal_narrative_context_and_references(self):
        internal = self._requirement(title='SECRET requirement')
        public = self._requirement(audience='customer')
        question = self._context(title='SECRET question')
        decision = self._context('decision', title='SECRET decision', audience='customer')
        deliverable = self._context('deliverable', title='Public deliverable', audience='customer', affected_requirement_revision_ids=[Command.set((public | internal).ids)])
        baseline, _ = self._approved(public | internal, context_revision_ids=[Command.set((question | decision | deliverable).ids)],
            section_ids=[Command.create({'title': 'SECRET section', 'body': '<p>SECRET narrative</p>'}),
                         Command.create({'title': 'Public scope', 'audience': 'customer', 'body': '<p>Own requests only.</p>'})])
        customer = baseline.with_user(self.user).action_projection('customer')
        serialized = json.dumps(customer)
        self.assertNotIn('SECRET', serialized)
        self.assertNotIn('revision_id', serialized)
        self.assertNotIn('owner_id', serialized)
        self.assertEqual(len(customer['requirements']), 1)
        self.assertEqual(len(customer['contexts'][0]['requirements']), 1)
        html = self._html(baseline, 'customer', audience='internal', projection={'title': 'SECRET injected'})
        self.assertNotIn('SECRET', html)
        self.assertIn('not the full internal baseline', html)
        self.assertIn('SECRET', self._html(baseline))

    def test_native_qweb_escapes_text_markup_and_never_embeds_external_resources(self):
        attack = '<img src="https://example.invalid/secret" onerror="window.solutionInjected=true">'
        requirement = self._requirement(title=attack, description='<script>window.solutionInjected=true</script>', audience='customer')
        baseline, _ = self._approved(requirement, section_ids=[Command.create({'title': 'Safe section', 'audience': 'customer', 'body': '<p>Real text</p>' + attack})])
        html = self._html(baseline, 'customer')
        self.assertIn('&lt;img', html)
        self.assertIn('&lt;script', html)
        self.assertNotIn('<img src="https://example.invalid', html)
        self.assertNotIn('<script>window.solutionInjected', html)
        self.assertIn('Real text', html)
        self.assertFalse(self.env.ref('project_agile_solution.report_solution_customer_action').attachment_use)
        self.assertFalse(self.env.ref('project_agile_solution.report_solution_customer_action').attachment)

    def test_exact_baseline_stays_reproducible_after_rename_archive_and_successor(self):
        baseline, requirement = self._approved()
        before = baseline.action_projection('customer')
        successor = baseline.browse(baseline.action_new_revision()['res_id'])
        successor.write({'title': 'New unapproved proposal'})
        self.document.write({'name': 'Changed document name'})
        requirement.requirement_id.write({'name': 'Changed identity name', 'active': False})
        self.assertEqual(baseline.action_projection('customer'), before)
        self.assertIn('Unapproved', successor.action_projection()['approval_notice'])
        self.assertEqual(successor.state, 'draft')
        self.assertIn('SYNTHETIC baseline', self._html(baseline))

    def test_inaccessible_any_required_reference_refuses_both_audiences_and_exports(self):
        requirement = self._requirement()
        spike = self._spike()
        question = self._context(spike_task_ids=[Command.set(spike.ids)])
        baseline, _ = self._approved(requirement, context_revision_ids=[Command.set(question.ids)])
        wizard = self.env['project.agile.solution.preview.wizard'].with_user(self.user).create({'revision_id': baseline.id, 'audience': 'customer'})
        wizard.read(['projection_text'])
        for model, row in ((requirement._name, requirement), (question._name, question), ('project.task', spike), ('project.project', self.project)):
            rule = self._hide(model, row)
            for audience in ('internal', 'customer'):
                with self.assertRaises(AccessError):
                    baseline.with_user(self.user).action_projection(audience)
                with self.assertRaises(AccessError):
                    self._html(baseline, audience)
            with self.assertRaises(AccessError):
                wizard.read(['projection_text'])
            with self.assertRaises(AccessError):
                wizard.export_data(['projection_text'])
            rule.unlink()

    def test_draft_hidden_members_cannot_render_as_complete(self):
        requirement = self._requirement()
        draft = self._revision(requirement_revision_ids=[Command.set(requirement.ids)])
        self._hide(requirement._name, requirement)
        for audience in ('internal', 'customer'):
            with self.assertRaises(AccessError):
                draft.action_projection(audience)

    def test_direct_report_model_rejects_portal_sudo_and_forged_exact_ids(self):
        baseline, _ = self._approved()
        report = self.env['report.project_agile_solution.report_solution_customer']
        for ids in ([True], ['1'], [], baseline.ids * 2, [-1]):
            with self.assertRaises(ValidationError):
                report.with_user(self.user)._get_report_values(ids)
        for user in (self.portal, self.env.ref('base.public_user')):
            with self.assertRaises(AccessError):
                report.with_user(user).sudo()._get_report_values(baseline.ids)
        with self.assertRaises(ValidationError):
            baseline.action_projection('public')

    def test_native_wizard_form_export_and_report_choose_exact_audience(self):
        baseline, _ = self._approved()
        with Form(self.env['project.agile.solution.preview.wizard'].with_user(self.user)) as form:
            form.revision_id = baseline.with_user(self.user)
            form.audience = 'customer'
        wizard = form.record
        self.assertEqual(wizard.action_render()['report_name'], 'project_agile_solution.report_solution_customer')
        exported = wizard.export_data(['projection_text', 'coverage_text'])['datas'][0]
        self.assertIn('not the full internal baseline', exported[0])
        self.assertIn('internal only', exported[1])
        with self.assertRaises(ValidationError):
            wizard.write({'projection_text': 'Fake approved document'})

    def test_explicit_acceptance_binds_authority_criteria_evidence_and_exact_revision(self):
        baseline, requirement = self._approved()
        event = self._event(baseline, requirement)
        self.assertEqual(event.recorded_by_id, self.manager)
        self.assertEqual(event.recorded_by_label, self.manager.display_name)
        self.assertTrue(event.recorded_at)
        self.assertTrue(requirement.sealed)
        coverage = baseline.action_coverage()['categories']
        self.assertEqual(coverage['accepted_with_evidence'][0]['evidence'], event.evidence)
        self.assertEqual(coverage['approved_but_unaccepted'], [])
        successor = requirement.browse(requirement.requirement_id.action_new_revision()['res_id'])
        with self.assertRaises(ValidationError):
            self._event(baseline, successor)
        self.assertEqual(event.requirement_revision_id, requirement)

    def test_acceptance_does_not_follow_done_or_merge_and_withdrawal_appends(self):
        baseline, requirement = self._approved()
        task = self._spike(item_type='story')
        task.write({'state': '1_done'})
        self.assertFalse(baseline.action_coverage()['categories']['accepted_with_evidence'])
        first = self._event(baseline, requirement)
        second = self._event(baseline, requirement, decision='withdrawn', evidence='SYNTHETIC negative evidence contradicts acceptance')
        self.assertEqual(second.supersedes_id, first)
        self.assertEqual(first.decision, 'accepted')
        coverage = baseline.action_coverage()['categories']
        self.assertFalse(coverage['accepted_with_evidence'])
        self.assertEqual(coverage['rejected_or_withdrawn'][0]['decision'], 'withdrawn')
        for record in (first, first.sudo()):
            with self.assertRaises(AccessError):
                record.write({'evidence': 'Rewrite'})
            with self.assertRaises(AccessError):
                record.unlink()

    def test_acceptance_rejects_unapproved_unrelated_missing_evidence_and_audit(self):
        requirement = self._requirement()
        draft = self._revision(requirement_revision_ids=[Command.set(requirement.ids)])
        with self.assertRaises(ValidationError):
            self._event(draft, requirement)
        self._approve(draft)
        for values in ({'evidence': ''}, {'criteria_evaluated': ' '}, {'authority_label': ''}, {'recorded_by_id': self.user.id}, {'recorded_at': '2020-01-01'}, {'supersedes_id': True}, {'decision': 'done'}, {'requirement_revision_id': True}):
            with self.assertRaises(ValidationError):
                self._event(draft, requirement, **values)
        unrelated = self._requirement()
        with self.assertRaises(ValidationError):
            self._event(draft, unrelated)
        self.assertFalse(self.env['project.agile.requirement.acceptance'].search([]))

    def test_other_manager_and_user_cannot_assert_exact_baseline_authority(self):
        baseline, requirement = self._approved()
        values = {'document_revision_id': baseline.id, 'requirement_revision_id': requirement.id, 'decision': 'accepted', 'authority_label': 'Forgery', 'criteria_evaluated': 'Forgery', 'evidence': 'Forgery'}
        for user in (self.user, self.portal):
            with self.assertRaises(AccessError):
                self.env['project.agile.requirement.acceptance'].with_user(user).sudo().create(values)
        self.user.write({'group_ids': [Command.link(self.env.ref('project.group_project_manager').id)]})
        with self.assertRaises(AccessError):
            self.env['project.agile.requirement.acceptance'].with_user(self.user).create(values)
        self.document.write({'approver_id': self.user.id})
        with self.assertRaises(AccessError):
            self.env['project.agile.requirement.acceptance'].with_user(self.user).create(values)
        self._event(baseline, requirement)

    def test_superseded_acceptance_remains_historical_and_can_be_withdrawn_not_extended(self):
        baseline, requirement = self._approved()
        accepted = self._event(baseline, requirement)
        successor = baseline.browse(baseline.action_new_revision()['res_id'])
        self._approve(successor)
        self.assertEqual(baseline.state, 'superseded')
        self.assertTrue(baseline.action_coverage()['categories']['accepted_with_evidence'])
        self.assertFalse(successor.action_coverage()['categories']['accepted_with_evidence'])
        with self.assertRaises(ValidationError):
            self._event(baseline, requirement)
        withdrawn = self._event(baseline, requirement, decision='withdrawn', evidence='SYNTHETIC historical correction after supersession')
        self.assertEqual(withdrawn.supersedes_id, accepted)
        self.assertFalse(baseline.action_coverage()['categories']['accepted_with_evidence'])

    def test_acceptance_cached_read_search_group_export_and_company_deny(self):
        baseline, requirement = self._approved()
        event = self._event(baseline, requirement).with_user(self.user)
        event.read(['evidence'])
        rule = self._hide(requirement._name, requirement)
        self.assertEqual(event.search_count([('id', '=', event.id)]), 0)
        self.assertEqual(event._read_group([('id', '=', event.id)], ['requirement_revision_id'], ['__count']), [])
        self.assertEqual(event.name_search('SYNTHETIC scope owner'), [])
        for action in (lambda: event.read(['evidence']), lambda: event.export_data(['evidence'])):
            with self.assertRaises(AccessError):
                action()
        rule.unlink()
        self.user.write({'company_ids': [Command.set(self.other_company.ids)], 'company_id': self.other_company.id})
        with self.assertRaises(AccessError):
            event.with_context(allowed_company_ids=self.other_company.ids).read(['evidence'])

    def test_batch_acceptance_failure_has_no_partial_event_or_seal(self):
        baseline, requirement = self._approved()
        event = self._event(baseline, requirement)
        values = {key: event[key].id if key.endswith('_id') else event[key] for key in ('document_revision_id', 'requirement_revision_id', 'decision', 'authority_label', 'criteria_evaluated', 'evidence')}
        count = event.search_count([])
        with self.assertRaises(ValidationError):
            event.create([values, {**values, 'evidence': ''}])
        self.assertEqual(event.search_count([]), count)

    def test_native_acceptance_form_and_forged_defaults_preserve_authenticated_recorder(self):
        baseline, requirement = self._approved()
        model = self.env['project.agile.requirement.acceptance'].with_user(self.manager).with_context(
            default_recorded_by_id=self.user.id, default_recorded_by_label='Forgery', default_supersedes_id=True)
        with Form(model) as form:
            form.requirement_revision_id = requirement
            form.document_revision_id = baseline
            form.decision = 'accepted'
            form.authority_label = 'SYNTHETIC asserted evaluator'
            form.criteria_evaluated = 'Explicit own-request negative identity matrix'
            form.evidence = '<script>fixture literal evidence</script>'
        event = form.record
        self.assertEqual(event.recorded_by_id, self.manager)
        self.assertEqual(event.recorded_by_label, self.manager.display_name)
        self.assertFalse(event.supersedes_id)
        exported = event.with_user(self.user).export_data(['evidence', 'recorded_by_label'])['datas']
        self.assertEqual(exported, [[event.evidence, self.manager.display_name]])
        coverage = baseline.action_coverage()['categories']['accepted_with_evidence'][0]
        self.assertIn('assertion', coverage['authority_notice'])
        self.assertEqual(coverage['authenticated_recorder'], self.manager.display_name)

    def test_native_pdf_entrypoint_checks_current_scope_and_does_not_reuse_attachment(self):
        baseline, requirement = self._approved()
        reports = self.env['ir.actions.report'].with_user(self.user)
        content, kind = reports._render_qweb_pdf('project_agile_solution.report_solution_customer', baseline.ids)
        # Odoo's native test-mode fallback may return HTML; still exercise the
        # actual PDF entrypoint and its current-user hook, not a mocked report.
        self.assertIn(kind, ('html', 'pdf'))
        self.assertTrue(content)
        self.assertFalse(self.env['ir.attachment'].search([('res_model', '=', baseline._name), ('res_id', '=', baseline.id)]))
        self._hide(requirement._name, requirement)
        with self.assertRaises(AccessError):
            reports._render_qweb_pdf('project_agile_solution.report_solution_customer', baseline.ids)

    def test_preview_literal_ids_and_inaccessible_baseline_defaults_are_not_authority(self):
        baseline, requirement = self._approved()
        model = self.env['project.agile.solution.preview.wizard'].with_user(self.user)
        for record_id in (True, str(baseline.id), -1):
            with self.assertRaises(ValidationError):
                model.create({'revision_id': record_id})
        rule = self._hide(baseline._name, baseline)
        with self.assertRaises(AccessError):
            model.with_context(default_revision_id=baseline.id).create({})
        rule.unlink()
        wizard = model.create({'revision_id': baseline.id})
        for record_id in (True, str(baseline.id), -1):
            with self.assertRaises(ValidationError):
                wizard.write({'revision_id': record_id})

    def test_coverage_distinguishes_old_links_maintenance_questions_and_change(self):
        baseline, requirement = self._approved(context_revision_ids=[Command.set(self._context().ids)])
        task = self._spike(item_type='story')
        self.env['project.agile.requirement.task.link'].with_user(self.manager).create({'task_id': task.id, 'requirement_revision_id': requirement.id})
        maintenance = self._spike(item_type='task')
        maintenance.write({'solution_maintenance_reason': 'SYNTHETIC development maintenance'})
        newer = requirement.browse(requirement.requirement_id.action_new_revision()['res_id'])
        newer.write({'title': 'Revised expectations'})
        draft = baseline.browse(baseline.action_new_revision()['res_id'])
        draft.write({'requirement_revision_ids': [Command.set(newer.ids)]})
        coverage = draft.action_coverage(baseline.id)['categories']
        self.assertEqual(len(coverage['older_revision_work']), 1)
        self.assertEqual(len(coverage['unlinked_requirements']), 1)
        self.assertEqual(len(coverage['legitimate_unlinked_maintenance']), 1)
        self.assertEqual(len(coverage['unresolved_questions_affecting_work']), 1)
        self.assertEqual(coverage['changes_since_baseline']['requirements']['changed'], [requirement.requirement_id.key])
        self.assertFalse(coverage['accepted_with_evidence'])
        self.assertNotIn('percentage', coverage)

    def test_coverage_refuses_hidden_work_instead_of_false_unlinked_complete(self):
        baseline, requirement = self._approved()
        task = self._spike(item_type='story')
        self.env['project.agile.requirement.task.link'].with_user(self.manager).create({'task_id': task.id, 'requirement_revision_id': requirement.id})
        baseline.with_user(self.user).action_coverage()
        self._hide('project.task', task)
        with self.assertRaises(AccessError):
            baseline.with_user(self.user).action_coverage()
        self.assertIn('Own', baseline.action_projection('customer')['requirements'][0]['acceptance_expectations'])

    def test_comparison_requires_exact_same_document_approved_baseline(self):
        baseline, _ = self._approved()
        for value in (True, str(baseline.id), -1):
            with self.assertRaises(ValidationError):
                baseline.action_coverage(value)
        other = self.document.create({'name': 'Other', 'solution_id': self.solution.id, 'approver_id': self.manager.id})
        foreign = self._revision(document=other)
        self._approve(foreign)
        with self.assertRaises(ValidationError):
            baseline.action_coverage(foreign.id)

    def test_preview_requeries_hidden_scope_after_creation_and_blocks_projection_write(self):
        baseline, requirement = self._approved()
        wizard = self.env['project.agile.solution.preview.wizard'].with_user(self.user).create({'revision_id': baseline.id})
        wizard.read(['projection_text'])
        with self.assertRaises(ValidationError):
            wizard.write({'coverage_text': '100% complete'})
        self._hide(baseline._name, baseline)
        self.assertNotIn(wizard, wizard.search([]))
        with self.assertRaises(AccessError):
            wizard.read(['projection_text'])
        with self.assertRaises(AccessError):
            wizard.action_render()

    def test_three_synthetic_narratives_render_trace_and_accept_only_explicit_evidence(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/synthetic_scenarios.json').read_text())
        self.assertTrue(fixture['synthetic'])
        for scenario in fixture['scenarios']:
            seeded = seed_scenario(self.env, self.manager, self.company, scenario)
            for source in scenario['tasks']:
                task = seeded['tasks'][source['key']]
                if source.get('maintenance_reason'):
                    task.write({'solution_maintenance_reason': source['maintenance_reason']})
                for token in source['requirement_revisions']:
                    self.env['project.agile.requirement.task.link'].with_user(self.manager).create({'task_id': task.id,
                        'requirement_revision_id': seeded['requirements'][token.split('@')[0]].id, 'document_revision_id': seeded['spec'].id})
            rendered = self._html(seeded['spec'])
            self.assertIn(scenario['purpose'], rendered)
            self.assertIn('SYNTHETIC', rendered)
            self.assertNotIn('100%', rendered)
            coverage = seeded['spec'].action_coverage()['categories']
            self.assertFalse(coverage['accepted_with_evidence'])
            if scenario['id'] == 'portal':
                event = self._event(seeded['spec'], seeded['requirements']['FR1'], evidence=scenario['trace']['verification_reference'])
                self.assertEqual(event.decision, 'accepted')
                self.assertIn('Include own submission', self._html(seeded['sow'], 'customer'))
            if scenario['id'] == 'integration':
                self.assertTrue(coverage['unresolved_questions_affecting_work'])
            if scenario['id'] == 'internal':
                self.assertFalse(seeded['sow'])
                self.assertEqual(len(coverage['legitimate_unlinked_maintenance']), 1)

    def test_synthetic_integration_scope_revision_requires_separate_sow_then_spec_approval(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/synthetic_scenarios.json').read_text())
        scenario = next(row for row in fixture['scenarios'] if row['id'] == 'integration')
        seeded = seed_scenario(self.env, self.manager, self.company, scenario)
        old = seeded['requirements']['FR1']
        self.env['project.agile.requirement.task.link'].with_user(self.manager).create({
            'task_id': seeded['tasks']['T1'].id, 'requirement_revision_id': old.id, 'document_revision_id': seeded['spec'].id})
        new = old.browse(old.requirement_id.action_new_revision()['res_id'])
        new.write({'title': scenario['reviewed_scope_revision']['text'], 'description': scenario['reviewed_scope_revision']['text']})
        requirements = new | seeded['requirements']['NFR1']
        decision = self._context('decision', solution=seeded['solution'], title='SYNTHETIC inbound-only revision',
            decision_context=scenario['reviewed_scope_revision']['decision_context'], choice=scenario['reviewed_scope_revision']['text'],
            consequences=scenario['reviewed_scope_revision']['consequences'], affected_requirement_revision_ids=[Command.set(requirements.ids)])
        sow = seeded['sow'].browse(seeded['sow'].action_new_revision()['res_id'])
        sow.write({'scope_disposition': 'change', 'scope_change_reason': 'SYNTHETIC hypothesized inbound-only scope; not observed API evidence',
            'requirement_revision_ids': [Command.set(requirements.ids)], 'context_revision_ids': [Command.link(decision.id)]})
        spec = seeded['spec'].browse(seeded['spec'].action_new_revision()['res_id'])
        spec.write({'based_sow_revision_id': sow.id, 'scope_disposition': 'change', 'scope_change_reason': 'SYNTHETIC separate scope approval',
            'requirement_revision_ids': [Command.set(requirements.ids)], 'context_revision_ids': [Command.link(decision.id)]})
        spec.action_submit()
        with self.assertRaises(ValidationError):
            spec.action_approve()
        self._approve(sow)
        spec.action_return_to_draft('SYNTHETIC SOW now separately approved; resubmit exact reference')
        self._approve(spec)
        self.assertEqual((sow.state, spec.state), ('approved', 'approved'))
        coverage = spec.action_coverage(seeded['spec'].id)['categories']
        self.assertEqual(len(coverage['older_revision_work']), 1)
        self.assertEqual(coverage['changes_since_baseline']['requirements']['changed'], [old.requirement_id.key])
        self.assertFalse(coverage['accepted_with_evidence'])
        self.assertIn('not observed API evidence', sow.action_projection()['scope_change_reason'])

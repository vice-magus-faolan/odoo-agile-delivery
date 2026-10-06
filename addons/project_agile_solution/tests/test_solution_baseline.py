"""Actual native identities, approval separation and hostile mutation boundaries."""
from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, UserError, ValidationError


from .test_solution_lineage import TestSolutionLineage


class TestSolutionBaseline(TestSolutionLineage):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.second_manager = mail_new_test_user(cls.env, 'baseline_second_manager', groups='project.group_project_manager', company_id=cls.company.id, company_ids=[Command.set(cls.company.ids)])
        cls.document = cls.env['project.agile.solution.document'].with_user(cls.manager).create({
            'name': 'SYNTHETIC Internal Brief', 'solution_id': cls.solution.id,
            'kind': 'spec', 'approver_id': cls.manager.id,
        })

    _project = TestSolutionLineage.__dict__['_project']

    def _revision(self, document=None, **values):
        document = document or self.document
        return self.env['project.agile.solution.revision'].with_user(self.manager).create({
            'document_id': document.id, 'title': 'SYNTHETIC baseline',
            'section_ids': [Command.create({'title': 'Scope', 'body': '<p>Original included scope.</p>', 'sequence': 10})],
            **values,
        })

    def _approve(self, revision):
        revision.action_submit()
        revision.action_approve()

    def test_optional_internal_brief_and_exact_snapshot(self):
        revision = self._revision()
        self._approve(revision)
        snapshot = revision.snapshot_json
        self.assertEqual(revision.state, 'approved')
        self.assertEqual(revision.approved_by_id, self.manager)
        self.document.write({'name': 'Renamed', 'active': False})
        self.solution.with_user(self.manager).write({'name': 'Renamed lineage', 'active': False})
        self.project.write({'name': 'Renamed Project', 'active': False})
        self.assertEqual(revision.with_user(self.user).read(['snapshot_json'])[0]['snapshot_json'], snapshot)
        self.assertIn('Original included scope.', snapshot)
        self.assertIn('SYNTHETIC Internal Brief', snapshot)
        self.assertIn('SYNTHETIC Visible', snapshot)

    def test_review_freezes_content_and_explicit_return_reopens_draft(self):
        revision = self._revision()
        revision.action_submit()
        with self.assertRaises(ValidationError):
            revision.write({'title': 'Silent review edit'})
        with self.assertRaises(ValidationError):
            revision.section_ids.write({'body': 'Silent review edit'})
        revision.action_return_to_draft('Needs clearer exclusions')
        self.assertEqual(revision.state, 'draft')
        self.assertEqual(revision.return_reason, 'Needs clearer exclusions')
        revision.section_ids.write({'body': 'Explicit draft edit'})
        self._approve(revision)

    def test_direct_state_and_audit_fields_rejected_even_sudo_context(self):
        revision = self._revision()
        for record in (revision, revision.sudo(), revision.with_context(solution_trusted=True, skip_immutability=True)):
            for values in ({'state': 'approved'}, {'snapshot_json': '{}'}, {'approved_by_id': self.manager.id}, {'number': 99}, {'document_id': self.document.id}):
                with self.assertRaises(ValidationError):
                    record.write(values)
        with self.assertRaises(ValidationError):
            self._revision(state='approved')

    def test_approved_orm_import_x2many_and_sudo_mutations_fail(self):
        revision = self._revision()
        self._approve(revision)
        before = revision.snapshot_json
        for record in (revision, revision.sudo(), revision.with_context(solution_trusted=True)):
            for values in ({'title': 'Rewrite'}, {'active': False}, {'section_ids': [Command.clear()]}, {'section_ids': [Command.create({'title': 'Injected'})]}):
                with self.assertRaises(ValidationError), self.cr.savepoint():
                    record.write(values)
            with self.assertRaises(ValidationError):
                record.unlink()
        for section in (revision.section_ids, revision.section_ids.sudo()):
            with self.assertRaises(ValidationError):
                section.write({'sequence': 99})
            with self.assertRaises(ValidationError):
                section.unlink()
        self.env['ir.model.data'].create({'module': '__import__', 'name': 'baseline_immutable', 'model': revision._name, 'res_id': revision.id})
        result = revision.load(['id', 'title'], [['__import__.baseline_immutable', 'Injected']])
        self.assertTrue(result['messages'])
        self.assertEqual(revision.snapshot_json, before)

    def test_successor_is_distinct_and_supersession_preserves_content(self):
        first = self._revision()
        self._approve(first)
        snapshot = first.snapshot_json
        action = first.action_new_revision()
        second = self.env['project.agile.solution.revision'].with_user(self.manager).browse(action['res_id'])
        self.assertEqual(second.predecessor_id, first)
        self.assertEqual(second.number, 2)
        self.assertNotEqual(second.section_ids, first.section_ids)
        second.section_ids.write({'body': '<p>Explicit successor scope.</p>'})
        self.assertEqual(first.state, 'approved')
        self.assertEqual(first.snapshot_json, snapshot)
        self._approve(second)
        self.assertEqual(first.state, 'superseded')
        self.assertEqual(first.snapshot_json, snapshot)
        self.assertEqual(second.state, 'approved')

    def test_one_working_revision_and_no_copy_of_baseline(self):
        first = self._revision()
        with self.assertRaises(ValidationError):
            self._revision()
        self._approve(first)
        with self.assertRaises(ValidationError):
            first.copy()
        first.action_new_revision()
        with self.assertRaises(ValidationError):
            first.action_new_revision()

    def test_sow_and_spec_approval_are_independent(self):
        sow = self.document.create({'name': 'SYNTHETIC SOW', 'solution_id': self.solution.id, 'kind': 'sow', 'approver_id': self.manager.id})
        sow_revision = self._revision(sow)
        spec = self._revision(based_sow_revision_id=sow_revision.id)
        spec.action_submit()
        with self.assertRaises(ValidationError):
            spec.action_approve()
        self._approve(sow_revision)
        self.assertEqual(spec.state, 'review')
        spec.action_approve()
        self.assertEqual(spec.state, 'approved')
        self.assertEqual(sow_revision.state, 'approved')

    def test_expanded_spec_needs_explicit_changed_sow_successor(self):
        sow = self.document.create({'name': 'SOW', 'solution_id': self.solution.id, 'kind': 'sow', 'approver_id': self.manager.id})
        sow1 = self._revision(sow)
        self._approve(sow1)
        spec1 = self._revision(based_sow_revision_id=sow1.id)
        self._approve(spec1)
        spec2 = self.env['project.agile.solution.revision'].with_user(self.manager).browse(spec1.action_new_revision()['res_id'])
        spec2.write({'scope_disposition': 'change', 'scope_change_reason': 'Additional deliverable'})
        spec2.action_submit()
        with self.assertRaises(ValidationError):
            spec2.action_approve()
        spec2.action_return_to_draft('Await SOW change approval')
        sow2 = self.env['project.agile.solution.revision'].with_user(self.manager).browse(sow1.action_new_revision()['res_id'])
        sow2.write({'scope_disposition': 'change', 'scope_change_reason': 'Explicit additional deliverable approval'})
        self._approve(sow2)
        spec2.write({'based_sow_revision_id': sow2.id})
        self._approve(spec2)
        self.assertEqual(spec1.state, 'superseded')
        self.assertEqual(sow1.state, 'superseded')

    def test_non_designated_manager_reader_and_portal_cannot_approve(self):
        revision = self._revision()
        revision.action_submit()
        for user in (self.user, self.portal):
            with self.assertRaises(AccessError):
                revision.with_user(user).action_approve()
        self.document.approver_id = self.second_manager
        with self.assertRaises(AccessError):
            revision.action_approve()
        self.assertEqual(revision.state, 'review')

    def test_approver_cannot_be_inactive_or_non_manager(self):
        for approver in (self.user, self.portal):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self.document.write({'approver_id': approver.id})
        revision = self._revision()
        revision.action_submit()
        self.manager.active = False
        with self.assertRaises(AccessError):
            revision.action_approve()

    def test_current_native_rule_revocation_denies_actions_and_all_read_paths(self):
        revision = self._revision()
        self._approve(revision)
        revision.with_user(self.user).read(['snapshot_json'])
        rule = self.env['ir.rule'].create({'name': 'SYNTHETIC revoked Project', 'model_id': self.env.ref('project.model_project_project').id, 'domain_force': repr([('id', '!=', self.project.id)])})
        for model, record in (('project.agile.solution.document', self.document), ('project.agile.solution.revision', revision), ('project.agile.solution.section', revision.section_ids)):
            caller = self.env[model].with_user(self.user)
            self.assertEqual(caller.search_count([('id', '=', record.id)]), 0)
            self.assertEqual(caller._read_group([('id', '=', record.id)], ['project_id'], ['__count']), [])
            with self.assertRaises(AccessError):
                record.with_user(self.user).read(['display_name'])
            with self.assertRaises(AccessError):
                record.with_user(self.user).export_data(['display_name'])
        with self.assertRaises(AccessError):
            revision.sudo().action_new_revision()
        rule.unlink()
        revision.with_user(self.user).read(['snapshot_json'])

    def test_multi_company_foreign_ids_and_forged_context_denied(self):
        foreign_doc = self.env['project.agile.solution.document'].with_user(self.manager).with_context(allowed_company_ids=(self.company | self.other_company).ids).create({'name': 'Foreign', 'kind': 'sow', 'solution_id': self.foreign_solution.id, 'approver_id': self.manager.id})
        foreign_revision = self.env['project.agile.solution.revision'].with_env(foreign_doc.env).create({'document_id': foreign_doc.id, 'title': 'Foreign'})
        with self.assertRaises(AccessError):
            foreign_revision.with_user(self.user).read(['title'])
        for context in ({}, {'solution_trusted': True, 'allowed_company_ids': self.other_company.ids}):
            caller = self.env['project.agile.solution.revision'].with_user(self.manager).with_context(allowed_company_ids=self.company.ids).with_context(**context)
            with self.assertRaises(AccessError):
                caller.create({'document_id': self.document.id, 'title': 'Foreign scope', 'based_sow_revision_id': foreign_revision.id})
        both = self.env['project.agile.solution.revision'].with_user(self.manager).with_context(allowed_company_ids=(self.company | self.other_company).ids)
        # Native _check_company rejects this before our same-solution invariant.
        with self.assertRaises(UserError):
            both.create({'document_id': self.document.id, 'title': 'Cross solution', 'based_sow_revision_id': foreign_revision.id})
        other_solution = self.env['project.agile.solution'].with_user(self.manager).create({'name': 'Another same-company solution', 'project_id': self.project.id})
        other_document = self.document.create({'name': 'Another SOW', 'kind': 'sow', 'solution_id': other_solution.id, 'approver_id': self.manager.id})
        other_revision = self._revision(other_document)
        with self.assertRaises(ValidationError):
            self._revision(based_sow_revision_id=other_revision.id)
        with self.assertRaises(ValidationError):
            self.document.write({'solution_id': self.foreign_solution.id})

    def test_used_lineage_project_company_and_document_deletion_are_restricted(self):
        revision = self._revision()
        self._approve(revision)
        for record in (self.document, self.solution, self.project):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                record.unlink()
        with self.assertRaises(ValidationError):
            self.project.write({'company_id': self.other_company.id})
        self.project.write({'name': 'Allowed rename'})

    def test_draft_only_delete_and_batch_failure_rollback(self):
        revision = self._revision()
        revision.unlink()
        before = self.env['project.agile.solution.revision'].search_count([])
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['project.agile.solution.revision'].with_user(self.manager).create([
                {'document_id': self.document.id, 'title': 'Valid'},
                {'document_id': True, 'title': 'Invalid'},
            ])
        self.assertEqual(self.env['project.agile.solution.revision'].search_count([]), before)

    def test_template_copy_is_explicit_and_provenance_does_not_drift(self):
        template = self.env['project.agile.solution.template'].with_user(self.manager).create({'name': 'SYNTHETIC Template', 'kind': 'spec', 'company_id': self.company.id, 'sections_json': '[{"title":"Purpose","body":"<p>Original template</p>","sequence":10,"audience":"internal"}]'})
        revision = self._revision()
        revision.action_apply_template(template.id)
        provenance = revision.template_snapshot
        template.write({'sections_json': '[{"title":"Changed","body":"Changed"}]'})
        self.assertIn('Original template', revision.section_ids[-1].body)
        self.assertEqual(revision.template_snapshot, provenance)
        self._approve(revision)
        with self.assertRaises(ValidationError):
            revision.action_apply_template(template.id)

    def test_sanitized_sections_and_ordering_frozen(self):
        revision = self._revision()
        revision.write({'section_ids': [Command.create({'sequence': 5, 'title': 'First', 'body': '<p>Safe</p><script>alert(1)</script>', 'audience': 'customer'})]})
        self.assertNotIn('<script>', revision.section_ids.filtered(lambda s: s.title == 'First').body)
        self._approve(revision)
        self.assertLess(revision.snapshot_json.index('First'), revision.snapshot_json.index('Scope'))
        with self.assertRaises(ValidationError):
            revision.section_ids[0].write({'revision_id': self._revision(self.document.copy({'name': 'Other'})).id})

    def test_review_and_approval_revalidate_scope_and_stale_states(self):
        revision = self._revision()
        with self.assertRaises(ValidationError):
            revision.action_approve()
        revision.action_submit()
        with self.assertRaises(ValidationError):
            revision.action_submit()
        with self.assertRaises(ValidationError):
            revision.action_return_to_draft('')
        self._approve_after_review(revision)
        with self.assertRaises(ValidationError):
            revision.action_return_to_draft('Rewrite history')

    def _approve_after_review(self, revision):
        revision.action_approve()

    def test_snapshot_rechecks_hidden_section_after_prior_cached_read(self):
        revision = self._revision()
        self._approve(revision)
        caller = revision.with_user(self.user)
        caller.action_read_snapshot()
        caller.read(['snapshot_json'])
        rule = self.env['ir.rule'].create({'name': 'SYNTHETIC hidden section', 'model_id': self.env['ir.model']._get_id('project.agile.solution.section'), 'domain_force': repr([('id', '!=', revision.section_ids.id)])})
        for read in (lambda: caller.read(['snapshot_json']), lambda: caller.export_data(['snapshot_json']), caller.action_read_snapshot):
            with self.assertRaises(AccessError):
                read()
        rule.unlink()
        self.assertIn('Original included scope', caller.action_read_snapshot()['snapshot_json'])

    def test_hidden_document_protects_revision_search_and_section_read(self):
        revision = self._revision()
        self._approve(revision)
        self.env['ir.rule'].create({'name': 'SYNTHETIC hidden document', 'model_id': self.env['ir.model']._get_id('project.agile.solution.document'), 'domain_force': repr([('id', '!=', self.document.id)])})
        for record in (revision, revision.section_ids):
            self.assertEqual(record.with_user(self.user).search_count([('id', '=', record.id)]), 0)
            with self.assertRaises(AccessError):
                record.with_user(self.user).read(['display_name'])

    def _assert_raw_storage_denied(self, caller):
        self.assertFalse(caller.env.su)
        for field in ('_snapshot_content', '_snapshot_digest', '_template_content'):
            with self.subTest(field=field, operation='read'):
                with self.assertRaises(AccessError):
                    caller.read([field])
            with self.subTest(field=field, operation='export'):
                with self.assertRaises(AccessError):
                    caller.export_data([field])

    def test_raw_snapshot_storage_read_and_export_denied_in_debug(self):
        # Exercise the field boundary, not the independent native export role.
        self.manager.write({'group_ids': [Command.link(self.env.ref('base.group_allow_export').id)]})
        storage_group = self.env.ref('project_agile_solution.group_snapshot_storage')
        self.assertFalse(storage_group.user_ids)
        self.assertFalse(storage_group.implied_ids)
        self.assertFalse(storage_group.implied_by_ids)
        revision = self._revision()
        self._approve(revision)
        caller = revision.with_user(self.user)
        self.assertEqual(caller.state, 'approved')  # Row access is not storage authority.
        self._assert_raw_storage_denied(caller)
        with self.debug_mode():
            self.assertTrue(caller.env.user.has_group('base.group_no_one'))
            self.assertFalse(caller.env.user.has_group('project_agile_solution.group_snapshot_storage'))
            self._assert_raw_storage_denied(caller)
            self._assert_raw_storage_denied(revision.with_user(self.manager))

    def _assert_checked_storage_paths(self, caller, snapshot, provenance, denied=False):
        reads = (
            lambda: [caller.action_read_snapshot()['snapshot_json']],
            lambda: list(caller.read(['snapshot_json', 'template_snapshot'])[0][name] for name in ('snapshot_json', 'template_snapshot')),
            lambda: caller.export_data(['snapshot_json', 'template_snapshot'])['datas'][0],
        )
        for read in reads:
            if denied:
                with self.assertRaises(AccessError):
                    read()
            else:
                result = read()
                self.assertEqual(result[0], snapshot)
                if len(result) == 2:
                    self.assertEqual(result[1], provenance)

    def test_debug_checked_snapshot_and_template_revalidate_hidden_closure(self):
        revision = self._revision()
        template = self.env['project.agile.solution.template'].with_user(self.manager).create({
            'name': 'SYNTHETIC private provenance', 'kind': 'spec', 'company_id': self.company.id,
            'sections_json': '[{"title":"Internal narrative","body":"<p>SYNTHETIC_HIDDEN_STORAGE_TEXT</p>"}]',
        })
        revision.action_apply_template(template.id)
        self._approve(revision)
        snapshot = revision.snapshot_json
        provenance = revision.template_snapshot
        self.assertIn('SYNTHETIC_HIDDEN_STORAGE_TEXT', snapshot)
        self.assertIn('SYNTHETIC_HIDDEN_STORAGE_TEXT', provenance)
        caller = revision.with_user(self.user)
        self._assert_checked_storage_paths(caller, snapshot, provenance)
        with self.debug_mode():
            self._assert_checked_storage_paths(caller, snapshot, provenance)
        rule = self.env['ir.rule'].create({
            'name': 'SYNTHETIC hidden baseline storage section',
            'model_id': self.env['ir.model']._get_id('project.agile.solution.section'),
            'domain_force': repr([('id', '!=', revision.section_ids[0].id)]),
        })
        self._assert_checked_storage_paths(caller, snapshot, provenance, denied=True)
        with self.debug_mode():
            self._assert_raw_storage_denied(caller)
            self._assert_checked_storage_paths(caller, snapshot, provenance, denied=True)
        rule.unlink()
        with self.debug_mode():
            self._assert_checked_storage_paths(caller, snapshot, provenance)

    def test_hidden_sow_cannot_be_treated_as_optional(self):
        sow = self.document.create({'name': 'SOW', 'solution_id': self.solution.id, 'kind': 'sow', 'approver_id': self.manager.id})
        spec = self._revision()
        spec.action_submit()
        self.env['ir.rule'].create({'name': 'SYNTHETIC hidden SOW', 'model_id': self.env['ir.model']._get_id('project.agile.solution.document'), 'domain_force': repr([('id', '!=', sow.id)])})
        with self.assertRaises(AccessError):
            spec.action_approve()
        self.assertEqual(spec.state, 'review')

    def test_caller_defaults_cannot_forge_lifecycle_or_snapshot(self):
        revision = self.env['project.agile.solution.revision'].with_user(self.manager).with_context(default_state='approved', default_number=99, default_approved_by_id=self.manager.id, default_snapshot_json='Injected').create({'document_id': self.document.id, 'title': 'Safe default'})
        self.assertEqual(revision.state, 'draft')
        self.assertEqual(revision.number, 1)
        self.assertFalse(revision.snapshot_json)
        self.assertFalse(revision.approved_by_id)

    def test_x2many_reparenting_sealed_section_and_native_wizards(self):
        first = self._revision()
        self._approve(first)
        second = self.env['project.agile.solution.revision'].with_user(self.manager).browse(first.action_new_revision()['res_id'])
        with self.assertRaises(ValidationError), self.cr.savepoint():
            second.write({'section_ids': [Command.link(first.section_ids.id)]})
        self.assertEqual(first.section_ids.revision_id, first)
        second.action_submit()
        action = second.action_request_return()
        wizard = self.env[action['res_model']].with_user(self.manager).with_context(**action['context']).create({'reason': 'Explicit correction'})
        wizard.action_confirm()
        self.assertEqual(second.state, 'draft')
        with self.assertRaises(AccessError):
            wizard.with_user(self.user).action_confirm()

    def test_document_batch_constraint_failure_is_atomic_without_outer_savepoint(self):
        documents = self.env['project.agile.solution.document'].with_user(self.manager)
        before = documents.search_count([])
        with self.assertRaises(ValidationError):
            documents.create([{'name': 'Valid', 'solution_id': self.solution.id, 'approver_id': self.manager.id}, {'name': 'Invalid approver', 'solution_id': self.solution.id, 'approver_id': self.user.id}])
        self.assertEqual(documents.search_count([]), before)

    def test_working_edits_do_not_mutate_native_tasks(self):
        task = self.env['project.task'].with_user(self.user).create({'name': 'SYNTHETIC manual task', 'project_id': self.project.id, 'description': 'Manual description'})
        values = task.read(['description', 'state', 'agile_story_points', 'agile_acceptance_criteria'])
        revision = self._revision()
        self._approve(revision)
        successor = self.env['project.agile.solution.revision'].with_user(self.manager).browse(revision.action_new_revision()['res_id'])
        successor.section_ids.write({'body': 'Discovered additional work, not authorized'})
        self.assertEqual(task.read(['description', 'state', 'agile_story_points', 'agile_acceptance_criteria']), values)

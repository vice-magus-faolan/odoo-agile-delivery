"""Exact requirement/context membership extends, never replaces, document baselines."""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .solution_content import check_reference_commands
from .solution_access import lock_records

MEMBERS = {'requirement_revision_ids': 'project.agile.requirement.revision',
           'context_revision_ids': 'project.agile.solution.context.revision'}


class SolutionRevisionContent(models.Model):
    _inherit = 'project.agile.solution.revision'

    requirement_revision_ids = fields.Many2many('project.agile.requirement.revision', 'solution_document_requirement_rel', 'document_revision_id', 'requirement_revision_id', check_company=True, copy=False)
    context_revision_ids = fields.Many2many('project.agile.solution.context.revision', 'solution_document_context_rel', 'document_revision_id', 'context_revision_id', check_company=True, copy=False)

    @api.model
    def default_get(self, names):
        values = super().default_get([name for name in names if name not in MEMBERS])
        for name in MEMBERS:
            values.pop(name, None)
        return values

    def _check_membership_input(self, values):
        for name in MEMBERS:
            if name in values:
                check_reference_commands(values[name])

    def _create_draft(self, values):
        self._check_membership_input(values)
        return super()._create_draft(values)

    def write(self, values):
        self._check_membership_input(values)
        return super().write(values)

    def _validate_content(self):
        super()._validate_content()
        for record in self:
            for name in MEMBERS:
                members = record.with_context(active_test=False)[name].sudo(False)
                members.check_access('read')
                # Many2many fetching filters inaccessible targets; sudo field
                # values can also inherit a cached filtered relation. Query the
                # inverse relation instead of treating either cache as complete.
                total = self.env[MEMBERS[name]].sudo().search_count([('document_revision_ids', 'in', record.ids)])
                if len(members) != total:
                    raise AccessError(_('Required solution content is unavailable under current access.'))
                members._validate_content()
                if any(row.solution_id != record.solution_id for row in members):
                    raise ValidationError(_('Exact content must belong to the same solution.'))
                identities = members[members._identity_field]
                if len(identities) != len(members):
                    raise ValidationError(_('Select only one exact revision of each identity per document.'))

    def _snapshot_payload(self):
        payload = super()._snapshot_payload()
        payload.update(requirements=[row._snapshot_values() for row in self.requirement_revision_ids.sorted('id')],
                       contexts=[row._snapshot_values() for row in self.context_revision_ids.sorted(lambda row: (row.sequence, row.id))])
        return payload

    def _check_snapshot_closure(self, payload):
        super()._check_snapshot_closure(payload)
        for name, model in (('requirements', MEMBERS['requirement_revision_ids']), ('contexts', MEMBERS['context_revision_ids'])):
            for values in payload.get(name, []):
                self.env[model].sudo(False).with_context(active_test=False).browse(values['revision_id'])._check_snapshot_reference(values)

    def action_submit(self):
        caller = self._transition_caller('draft')
        with self.env.cr.savepoint():
            caller._validate_content()
            caller.requirement_revision_ids._seal()
            caller.context_revision_ids._seal()
            return super().action_submit()

    def action_new_revision(self):
        with self.env.cr.savepoint():
            action = super().action_new_revision()
            successor = self.env[self._name].browse(action['res_id'])
            successor.write({name: [(6, 0, self[name].ids)] for name in MEMBERS})
            return action


class SolutionContextRetention(models.Model):
    _inherit = 'project.task'

    # A storage-only inverse enables an ORM completeness query without exposing
    # hidden question IDs through ordinary Task read/debug/export surfaces.
    solution_question_revision_ids = fields.Many2many('project.agile.solution.context.revision',
        'solution_question_spike_rel', 'task_id', 'context_revision_id', readonly=True, copy=False,
        groups='project_agile_solution.group_snapshot_storage')

    @api.model
    def default_get(self, names):
        values = super().default_get([name for name in names if name != 'solution_question_revision_ids'])
        values.pop('solution_question_revision_ids', None)
        return values

    @api.model_create_multi
    def create(self, vals_list):
        if any('solution_question_revision_ids' in values for values in vals_list):
            raise ValidationError(_('Edit discovery references only through working question context.'))
        return super().create(vals_list)

    def write(self, values):
        if 'solution_question_revision_ids' in values:
            raise ValidationError(_('Edit discovery references only through working question context.'))
        return super().write(values)

    def unlink(self):
        self.sudo(False).check_access('unlink')
        lock_records(self, serialize=True)
        # A boolean retention guard never returns elevated Task/context metadata.
        if self.env['project.agile.solution.context.revision'].sudo().search_count([('spike_task_ids', 'in', self.ids)], limit=1):
            raise ValidationError(_('Referenced discovery work must be retained; archive instead.'))
        return super().unlink()

"""Shared current-caller authority and serialized scope locking."""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL

from .project_agile_solution import ProjectAgileSolution


def lock_records(records, serialize=False):
    """Serialize immutable-history operations, never commit an owned transaction.

    ORM has no row-lock primitive. The fixed model table and parameterized IDs
    are the sole SQL boundary; flush before lock and invalidate after waiting.
    Identity serialization performs an id=id MVCC write. An unchanged FOR UPDATE
    lock cannot refresh a repeatable-read snapshot after a wait; the no-op write
    forces stale contenders through native transaction retry without changing
    business fields, approved content or write_date.
    """
    if records:
        records.flush_recordset()
        records.env.cr.execute(SQL(
            'SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE',
            SQL.identifier(records._table), tuple(records.ids),
        ))
        if serialize:
            records.env.cr.execute(SQL('UPDATE %s SET id = id WHERE id IN %s', SQL.identifier(records._table), tuple(records.ids)))
        records.invalidate_recordset()


class SolutionAccess(models.AbstractModel):
    _name = 'project.agile.solution.access'
    _description = 'Current Native Solution Project Authority'

    solution_id = fields.Many2one('project.agile.solution')
    project_id = fields.Many2one(related='solution_id.project_id', store=True, index=True)
    company_id = fields.Many2one(related='project_id.company_id', store=True, index=True)
    native_project_access = fields.Boolean(
        compute='_compute_native_project_access', search='_search_native_project_access',
    )

    _compute_native_project_access = ProjectAgileSolution._compute_native_project_access

    @api.model
    def default_get(self, names):
        values = super().default_get(names)
        for name in ('project_id', 'company_id', 'native_project_access'):
            values.pop(name, None)
        if self._fields['solution_id'].related:
            values.pop('solution_id', None)
        return values

    def _search_native_project_access(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented
        parents = {
            'project.agile.solution.document': ('solution_id', 'project.agile.solution'),
            'project.agile.solution.revision': ('document_id', 'project.agile.solution.document'),
            'project.agile.solution.section': ('revision_id', 'project.agile.solution.revision'),
            'project.agile.requirement': ('solution_id', 'project.agile.solution'),
            'project.agile.requirement.revision': ('requirement_id', 'project.agile.requirement'),
            'project.agile.solution.context': ('solution_id', 'project.agile.solution'),
            'project.agile.solution.context.revision': ('context_id', 'project.agile.solution.context'),
        }
        field, model = parents[self._name]
        parent = self.env[model].sudo(False).with_context(active_test=False)
        projects = self.env['project.project'].sudo(False).with_context(active_test=False)
        accessible = Domain.AND([Domain('project_id', 'in', projects._search([])), Domain(field, 'in', parent._search([]))])
        positive = Domain.OR(accessible if item is True else ~accessible for item in value if type(item) is bool)
        return positive if operator == 'in' else ~positive

    def _check_authority(self, operation='write'):
        """Ordinary sudo/context cannot select authority or bypass Project rules."""
        caller = self.sudo(False)
        caller.check_access(operation)
        if not caller.env.user.active or not caller.env.user.has_group('project.group_project_manager'):
            raise AccessError(_('An active Project Manager with current Project access is required.'))
        caller.project_id.check_access('read')
        caller.project_id.check_access('write')
        return caller

    def _checked_relation(self, model, record_id):
        if type(record_id) is not int or record_id <= 0:
            raise ValidationError(_('Select an available record in this solution.'))
        record = self.env[model].sudo(False).with_context(active_test=False).browse(record_id).exists()
        record.check_access('read')
        if not record:
            raise ValidationError(_('Select an available record in this solution.'))
        return record

    def _lock_scope(self):
        """All revision writers share lineage -> document -> revision order."""
        lock_records(self.solution_id, serialize=True)
        lock_records(self.project_id)
        documents = self if self._name == 'project.agile.solution.document' else self.document_id
        lock_records(documents)
        if self._name == 'project.agile.solution.revision':
            lock_records(self)

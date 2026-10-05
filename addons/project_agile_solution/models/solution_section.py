"""Ordered document-owned actual narrative content, frozen with its revision."""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SolutionSection(models.Model):
    _name = 'project.agile.solution.section'
    _inherit = 'project.agile.solution.access'
    _description = 'Solution Revision Narrative Section'
    _check_company_auto = True
    _order = 'sequence, id'
    _rec_name = 'title'

    revision_id = fields.Many2one('project.agile.solution.revision', required=True, index=True, ondelete='restrict', check_company=True, copy=False)
    solution_id = fields.Many2one(related='revision_id.solution_id', store=True, index=True)
    document_id = fields.Many2one(related='revision_id.document_id', store=True)
    sequence = fields.Integer(default=10)
    title = fields.Char(required=True)
    body = fields.Html(sanitize=True, sanitize_overridable=False)
    audience = fields.Selection([('internal', 'Internal Only'), ('customer', 'Customer Projection')], default='internal', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        self.sudo(False).check_access('create')
        for values in vals_list:
            if {'solution_id', 'document_id', 'project_id', 'company_id'} & values.keys():
                raise ValidationError(_('Section scope comes from its draft revision.'))
            revision = self._checked_relation('project.agile.solution.revision', values.get('revision_id'))
            revision._check_editable()
        with self.env.cr.savepoint():
            return super().create(vals_list)

    def write(self, values):
        self._check_authority()
        self.revision_id._check_editable()
        if {'revision_id', 'solution_id', 'document_id', 'project_id', 'company_id'} & values.keys():
            raise ValidationError(_('Sections cannot be moved; copy content to a new draft.'))
        return super().write(values)

    def unlink(self):
        self._check_authority('unlink')
        self.revision_id._check_editable()
        return super().unlink()

    def _copy_values(self):
        self.ensure_one()
        self.sudo(False).check_access('read')
        return {'sequence': self.sequence, 'title': self.title, 'body': self.body or '', 'audience': self.audience}

    def _snapshot_values(self):
        return {'section_id': self.id, **self._copy_values()}

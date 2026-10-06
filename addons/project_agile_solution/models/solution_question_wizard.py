"""Explicit native question-resolution form; the model action owns authority."""
from odoo import fields, models


class SolutionQuestionWizard(models.TransientModel):
    _name = 'project.agile.solution.question.wizard'
    _description = 'Record Working Question Resolution'

    context_revision_id = fields.Many2one('project.agile.solution.context.revision', required=True, ondelete='cascade')
    resolution = fields.Text(required=True)
    rationale = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        caller = self.sudo(False)
        caller.check_access('write')
        caller.context_revision_id.action_resolve(caller.resolution, caller.rationale)
        return {'type': 'ir.actions.act_window_close'}

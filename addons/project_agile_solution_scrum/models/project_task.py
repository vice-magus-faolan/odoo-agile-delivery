"""Preserve complete native Task/event atomicity for direct Python callers too."""
from odoo import models


class TaskScopeAtomicity(models.Model):
    _inherit = 'project.task'

    def write(self, values):
        with self.env.cr.savepoint():
            return super().write(values)

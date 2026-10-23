"""Internal exact-publication preview and deliberate issue."""

import json

from odoo import api, fields, models


# Follow the existing SolutionPreviewWizard colocation of transient UI adapters.
# pylint: disable-next=no-wizard-in-models
class SolutionPortalIssueWizard(models.TransientModel):
    _name = "project.agile.solution.portal.issue.wizard"
    _description = "Preview and Issue Exact Customer Publication"

    revision_id = fields.Many2one("project.agile.solution.revision", required=True)
    recipient_id = fields.Many2one("res.users", required=True)
    preview_text = fields.Text(compute="_compute_preview", compute_sudo=False)

    @api.depends("revision_id")
    def _compute_preview(self):
        for row in self:
            row.preview_text = (
                json.dumps(
                    row.revision_id.action_portal_preview(),
                    ensure_ascii=False,
                    indent=2,
                )
                if row.revision_id
                else False
            )

    def action_issue(self):
        self.ensure_one()
        self.check_access("read")
        publication_id = self.revision_id.action_issue_portal(self.recipient_id.id)
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "project.agile.solution.portal.publication",
            "res_id": publication_id,
        }

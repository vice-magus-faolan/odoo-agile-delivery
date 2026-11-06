"""Customer-only adapters on native shared work, not source-model access grants."""

from odoo import _, models
from odoo.exceptions import AccessError

from .solution_discussion import source_readable

CUSTOMER_SUBTYPE = "project_agile_solution.mt_requirement_customer"


class CustomerRequirementDiscussion(models.Model):
    _inherit = "project.agile.requirement"

    def action_compose_customer_discussion(self):
        self.ensure_one()
        if not source_readable(self):
            raise AccessError(_("Current Solution source access is required."))
        return {
            "name": _("Customer discussion: shared text only"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_composition_mode": "comment",
                "default_subtype_xmlid": CUSTOMER_SUBTYPE,
            },
        }

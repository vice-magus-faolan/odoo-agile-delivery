# Native two-step selected-link refinement with current reference visibility.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


# Match the existing finite Solution wizard layout.
# pylint: disable-next=no-wizard-in-models
class RequirementRefineWizard(models.TransientModel):
    _name = "project.agile.requirement.refine.wizard"
    _description = "Refine Selected Task Acceptance Expectations"

    link_id = fields.Many2one(
        "project.agile.requirement.task.link",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    previous_expectations = fields.Text(
        related="link_id.requirement_revision_id.acceptance_expectations",
        readonly=True,
        compute_sudo=False,
    )
    acceptance_expectations = fields.Text(required=True)
    native_link_access = fields.Boolean(
        compute="_compute_link_access",
        search="_search_link_access",
    )

    def _compute_link_access(self):
        for wizard in self:
            wizard.native_link_access = True

    def _search_link_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        links = (
            self.env["project.agile.requirement.task.link"]
            .sudo(False)
            .with_context(active_test=False)
        )
        accessible = Domain("link_id", "in", links._search([]))
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    @api.model
    def default_get(self, names):
        # Opening uses an explicit saved dialog, not ambient defaults.
        return super().default_get([])

    @api.model_create_multi
    def create(self, vals_list):
        caller = self.sudo(False)
        caller.check_access("create")
        with self.env.cr.savepoint():
            for values in vals_list:
                if set(values) - {"link_id", "acceptance_expectations"}:
                    raise ValidationError(
                        _("Select a work link and proposed expectations only.")
                    )
                link = caller.env[
                    "project.agile.requirement.task.link"
                ]._checked_relation(
                    "project.agile.requirement.task.link", values.get("link_id")
                )
                link._check_refinement_source()
            return super(RequirementRefineWizard, caller).create(vals_list)

    def _check_current_link(self):
        caller = self._origin.sudo(False)
        caller.check_access("read")
        caller.link_id._check_current_trace_read()
        caller.link_id._trace_authority()
        return caller

    def read(self, fields=None, load="_classic_read"):
        self._check_current_link()
        return super().read(fields, load)

    def export_data(self, fields_to_export):
        self._check_current_link()
        return super().export_data(fields_to_export)

    def write(self, values):
        self._check_current_link()
        if set(values) - {"acceptance_expectations"}:
            raise ValidationError(
                _("The original work link is immutable; reopen refinement.")
            )
        return super().write(values)

    def action_confirm(self):
        self.ensure_one()
        caller = self._check_current_link()
        caller.check_access("write")
        return caller.link_id.action_refine_acceptance(caller.acceptance_expectations)

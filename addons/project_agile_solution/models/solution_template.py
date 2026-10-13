"""Small reusable narrative templates, explicitly copied with content provenance."""

import json

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import html_sanitize

from .solution_access import lock_records


class SolutionTemplate(models.Model):
    _name = "project.agile.solution.template"
    _description = "Solution Narrative Template"
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    kind = fields.Selection(
        [("sow", "Statement of Work"), ("spec", "Internal Brief / Specification")],
        required=True,
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, ondelete="restrict"
    )
    version = fields.Integer(default=1, readonly=True, copy=False)
    sections_json = fields.Text(required=True, default="[]")

    def _check_manager(self, operation):
        # Native XML installation uses actual uid=1 (not an active business
        # approver). Ordinary sudo preserves uid, so it cannot select this path.
        # Templates have no approval authority or protected sealed history.
        if self.env.uid == SUPERUSER_ID:
            return
        caller = self.sudo(False)
        caller.check_access(operation)
        if not caller.env.user.active or not caller.env.user.has_group(
            "project.group_project_manager"
        ):
            raise AccessError(_("Template editing requires an active Project Manager."))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_manager("create")
        if any("version" in values for values in vals_list):
            raise ValidationError(_("Template version is server managed."))
        return super().create([dict(values, version=1) for values in vals_list])

    def write(self, values):
        self._check_manager("write")
        lock_records(self)
        if {"version", "company_id"} & values.keys():
            raise ValidationError(_("Template version/company cannot be reassigned."))
        for record in self:
            super(SolutionTemplate, record).write(
                dict(values, version=record.version + 1)
            )
        return True

    def unlink(self):
        self._check_manager("unlink")
        return super().unlink()

    @api.constrains("sections_json")
    def _check_sections(self):
        for record in self:
            record._validated_sections()

    def _validated_sections(self):
        self.ensure_one()
        self.sudo(False).check_access("read")
        if len(self.sections_json or "") > 200000:
            raise ValidationError(_("Template content is too large."))
        try:
            sections = json.loads(self.sections_json)
        except (ValueError, TypeError) as error:
            raise ValidationError(
                _("Template sections must be a JSON array.")
            ) from error
        if type(sections) is not list or len(sections) > 100:
            raise ValidationError(_("Use at most 100 ordered narrative sections."))
        return [
            self._validated_section(section, index)
            for index, section in enumerate(sections)
        ]

    def _validated_section(self, section, index):
        if type(section) is not dict or set(section) - {
            "sequence",
            "title",
            "body",
            "audience",
        }:
            raise ValidationError(_("Unknown template section fields."))
        title, body = section.get("title"), section.get("body", "")
        sequence, audience = (
            section.get("sequence", (index + 1) * 10),
            section.get("audience", "internal"),
        )
        if type(title) is not str or not title.strip() or type(body) is not str:
            raise ValidationError(_("Each section needs a text title and HTML body."))
        if type(sequence) is not int or audience not in ("internal", "customer"):
            raise ValidationError(
                _("Use integer ordering and internal/customer audience.")
            )
        return {
            "title": title,
            "body": str(html_sanitize(body)),
            "sequence": sequence,
            "audience": audience,
        }

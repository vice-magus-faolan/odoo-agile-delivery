"""Bounded literal CI names, owned exclusively by an editable typed revision."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .policy_authority import clean_context, exact_name, lock_records, reject_keys


class ProjectGitPolicyRequiredCheck(models.Model):
    _name = "project.git.policy.required.check"
    _inherit = "project.git.policy.scope"
    _description = "Git Policy Exact Required Check"
    _check_company_auto = True

    revision_id = fields.Many2one(
        "project.git.policy.revision", required=True, ondelete="restrict", index=True
    )
    project_id = fields.Many2one(
        related="revision_id.project_id", store=True, readonly=True
    )
    company_id = fields.Many2one(
        related="revision_id.company_id", store=True, readonly=True
    )
    name = fields.Char(required=True)

    _name_unique = models.Constraint(
        "UNIQUE(revision_id, name)",
        "Each revision requires distinct exact check names.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        seen = set()
        for values in vals_list:
            reject_keys(values, {"revision_id", "name"})
            revision = self.env["project.git.policy.revision"].browse(
                values.get("revision_id")
            )
            revision._check_editable()
            revision.rule_id._lock_control()
            lock_records(revision)
            revision._check_editable()
            exact_name(values.get("name"), "Required check")
            identity = (revision.id, values["name"])
            if identity in seen or self.search_count(
                [("revision_id", "=", revision.id), ("name", "=", values["name"])]
            ):
                raise ValidationError(
                    _("Required check names must be distinct within the revision.")
                )
            seen.add(identity)
        records = super(
            # Remove forged defaults from this revision-bound creation.
            ProjectGitPolicyRequiredCheck,
            self.with_context(clean_context(self.env)),  # pylint: disable=context-overridden
        ).create(vals_list)
        records.revision_id._check_selectors()
        records.revision_id.rule_id._revoke("revision_changed")
        return records

    def write(self, values):
        self.check_access("write")
        reject_keys(values, {"name"})
        self.revision_id._check_editable()
        self.revision_id.rule_id._lock_control()
        lock_records(self.revision_id)
        self.revision_id._check_editable()
        exact_name(values.get("name"), "Required check")
        for record in self:
            if self.search_count(
                [
                    ("revision_id", "=", record.revision_id.id),
                    ("name", "=", values["name"]),
                    ("id", "!=", record.id),
                ]
            ):
                raise ValidationError(
                    _("Required check names must be distinct within the revision.")
                )
        self.revision_id.rule_id._revoke("revision_changed")
        return super().write(values)

    def unlink(self):
        self.check_access("unlink")
        self.revision_id._check_editable()
        self.revision_id.rule_id._lock_control()
        lock_records(self.revision_id)
        self.revision_id._check_editable()
        self.revision_id.rule_id._revoke("revision_changed")
        return super().unlink()

"""Project-stable requirements with exact FR/NFR delivery intent, never Tasks."""

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .solution_content import ContentRevision


class Requirement(models.Model):
    _name = "project.agile.requirement"
    _inherit = "project.agile.solution.content.identity"
    _description = "Stable Agile Requirement Identity"
    _check_company_auto = True
    _order = "project_id, key, id"
    _key_prefix = "REQ-"
    _identity_field = "requirement_id"
    _revision_model = "project.agile.requirement.revision"

    revision_ids = fields.One2many(
        "project.agile.requirement.revision",
        "requirement_id",
        readonly=True,
        copy=False,
    )
    _key_unique = models.Constraint(
        "UNIQUE(project_id, key)", "Requirement key must be unique within its Project."
    )


class RequirementRevision(models.Model):
    _name = "project.agile.requirement.revision"
    _inherit = "project.agile.solution.content.revision"
    _description = "Exact FR/NFR Requirement Revision"
    _check_company_auto = True
    _order = "requirement_id, number desc"
    _rec_name = "title"
    _identity_field = "requirement_id"
    _identity_model = "project.agile.requirement"
    _document_field = "requirement_revision_ids"
    _inverse_fields = frozenset({"document_revision_ids", "context_revision_ids"})

    requirement_id = fields.Many2one(
        "project.agile.requirement",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    solution_id = fields.Many2one(
        related="requirement_id.solution_id", store=True, index=True
    )
    predecessor_id = fields.Many2one(
        "project.agile.requirement.revision",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    requirement_type = fields.Selection(
        [("fr", "Functional"), ("nfr", "Nonfunctional")], required=True, default="fr"
    )
    description = fields.Text(required=True)
    rationale = fields.Text(required=True)
    priority = fields.Selection(
        [("must", "Must"), ("should", "Should"), ("could", "Could")],
        required=True,
        default="must",
    )
    verification_method = fields.Char(required=True)
    acceptance_expectations = fields.Text(required=True)
    document_revision_ids = fields.Many2many(
        "project.agile.solution.revision",
        "solution_document_requirement_rel",
        "requirement_revision_id",
        "document_revision_id",
        readonly=True,
        copy=False,
    )
    context_revision_ids = fields.Many2many(
        "project.agile.solution.context.revision",
        "solution_context_requirement_rel",
        "requirement_revision_id",
        "context_revision_id",
        readonly=True,
        copy=False,
    )
    _number_unique = models.Constraint(
        "UNIQUE(requirement_id, number)", "Requirement revision number must be unique."
    )

    _last_acceptance_id = fields.Many2one(
        "project.agile.requirement.acceptance",
        readonly=True,
        copy=False,
        ondelete="set null",
        groups="project_agile_solution.group_snapshot_storage",
        help=(
            "Published by acceptance append to order concurrent exact-revision "
            "decision history."
        ),
    )

    def _record_acceptance(self, event):
        self.ensure_one()
        if event.requirement_revision_id != self:
            raise ValidationError(_("Acceptance must retain its exact revision."))
        return super(ContentRevision, self.sudo()).write(
            {"_last_acceptance_id": event.id}
        )

    # Native validation is side-effect/error-only, not a write-result API.
    def _validate_content(self):  # pylint: disable=missing-return
        super()._validate_content()
        for record in self:
            for name in (
                "description",
                "rationale",
                "verification_method",
                "acceptance_expectations",
            ):
                if not (record[name] or "").strip():
                    raise ValidationError(
                        _(
                            "Requirements need rationale "
                            "and verifiable acceptance expectations."
                        )
                    )

    def _copy_content_values(self):
        return {
            **super()._copy_content_values(),
            **{
                name: self[name]
                for name in (
                    "requirement_type",
                    "description",
                    "rationale",
                    "priority",
                    "verification_method",
                    "acceptance_expectations",
                )
            },
        }

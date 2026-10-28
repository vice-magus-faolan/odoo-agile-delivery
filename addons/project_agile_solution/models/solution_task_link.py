"""Durable exact-revision edges; retiring working coverage never rewrites history."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.project_agile.utils import claim_records

from .solution_task_access import (
    check_document,
    check_requirements,
    check_task,
)

INPUT = frozenset({"task_id", "requirement_revision_id", "document_revision_id"})


class RequirementTaskLink(models.Model):
    _name = "project.agile.requirement.task.link"
    _inherit = "project.agile.solution.task.access"
    _description = "Native Task to Exact Requirement Revision"
    _check_company_auto = True
    _rec_name = "requirement_revision_id"

    task_id = fields.Many2one(
        "project.task",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    requirement_revision_id = fields.Many2one(
        "project.agile.requirement.revision",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    solution_id = fields.Many2one(
        related="requirement_revision_id.solution_id", store=True, index=True
    )
    document_revision_id = fields.Many2one(
        "project.agile.solution.revision", ondelete="restrict", check_company=True
    )
    active = fields.Boolean(default=True, readonly=True, copy=False)
    linked_by_id = fields.Many2one(
        "res.users", readonly=True, ondelete="restrict", copy=False
    )
    linked_at = fields.Datetime(readonly=True, copy=False)
    retired_by_id = fields.Many2one(
        "res.users", readonly=True, ondelete="restrict", copy=False
    )
    retired_at = fields.Datetime(readonly=True, copy=False)
    retirement_reason = fields.Text(readonly=True, copy=False)
    _edge_unique = models.Constraint(
        "UNIQUE(task_id, requirement_revision_id)",
        "This exact Task requirement edge already exists.",
    )

    _refinement_link_id = fields.Many2one(
        "project.agile.requirement.task.link",
        readonly=True,
        copy=False,
        ondelete="restrict",
        groups="project_agile_solution.group_snapshot_storage",
        help="Replacement exact edge retained for identical refinement retries.",
    )

    def _check_refinement_source(self):
        self.ensure_one()
        caller = self._trace_authority()
        caller._check_current_trace_read()
        check_task(caller.task_id, caller.project_id)
        revision = caller.requirement_revision_id
        revision._check_authority()
        check_requirements(revision, caller.solution_id)
        if (
            not caller.active
            or not revision.sealed
            or revision.requirement_id._complete_revisions()[-1] != revision
        ):
            raise ValidationError(
                _("Coverage changed; refine an active link to the current sealed head.")
            )
        return caller

    def action_request_refinement(self):
        caller = self._check_refinement_source()
        wizard = self.env["project.agile.requirement.refine.wizard"].create(
            {
                "link_id": caller.id,
                "acceptance_expectations": (
                    caller.requirement_revision_id.acceptance_expectations
                ),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_refine_acceptance(self, expectations):
        # Replace selected working coverage, never rewrite an exact agreement.
        self.ensure_one()
        caller = self._trace_authority()
        caller._check_current_trace_read()
        if (
            not isinstance(expectations, str)
            or not expectations.strip()
            or len(expectations) > 20000
        ):
            raise ValidationError(
                _("Give meaningful expectations of at most 20000 characters.")
            )
        with self.env.cr.savepoint():
            claim_records(caller.task_id, allow_referencing=True)
            claim_records(caller, allow_referencing=True)
            revision = caller.requirement_revision_id
            claim_records(revision.requirement_id, allow_referencing=True)
            claim_records(revision, allow_referencing=True)
            # Storage-only receipt is not authority to read or mutate its target.
            replacement = caller.browse(caller.sudo()._refinement_link_id.id)
            if replacement:
                replacement._trace_authority()
                replacement._check_current_trace_read()
                check_task(replacement.task_id, caller.project_id, active=False)
                if (
                    replacement.requirement_revision_id.acceptance_expectations
                    != expectations
                ):
                    raise ValidationError(
                        _("This link was refined with different expectations.")
                    )
            else:
                caller._check_refinement_source()
                if revision.acceptance_expectations == expectations:
                    raise ValidationError(
                        _("Change the expectations before applying refinement.")
                    )
                successor = revision.create(
                    {
                        **revision._copy_content_values(),
                        "requirement_id": revision.requirement_id.id,
                        "acceptance_expectations": expectations,
                    }
                )
                replacement = caller.create(
                    {
                        "task_id": caller.task_id.id,
                        "requirement_revision_id": successor.id,
                        "document_revision_id": False,
                    }
                )
                caller.action_retire(
                    _("Acceptance expectations refined in a numbered successor.")
                )
                super(RequirementTaskLink, caller.sudo()).write(
                    {"_refinement_link_id": replacement.id}
                )
            return {
                "type": "ir.actions.act_window",
                "res_model": "project.task",
                "res_id": replacement.task_id.id,
                "view_mode": "form",
            }

    @api.model
    def default_get(self, names):
        return {
            key: value
            for key, value in super()
            .default_get([name for name in names if name in INPUT])
            .items()
            if key in INPUT
        }

    @api.model_create_multi
    # _create_edge delegates only after exact-task/revision authorization.
    def create(self, vals_list):  # pylint: disable=method-required-super
        caller = self.sudo(False)
        caller.check_access("create")
        result = caller.browse()
        with self.env.cr.savepoint():
            for values in vals_list:
                result |= caller._create_edge(values)
        return result

    def _create_edge(self, values):
        if set(values) - INPUT:
            raise ValidationError(_("Link identity and audit are server managed."))
        revision = self._checked_relation(
            "project.agile.requirement.revision", values.get("requirement_revision_id")
        )
        revision._check_authority()
        task = self._checked_relation("project.task", values.get("task_id"))
        check_task(task, revision.project_id)
        claim_records(task, allow_referencing=True)
        claim_records(revision.project_id, allow_referencing=True)
        claim_records(revision.solution_id, allow_referencing=True)
        claim_records(revision.requirement_id, allow_referencing=True)
        claim_records(revision, allow_referencing=True)
        check_task(task, revision.project_id)
        check_requirements(revision, revision.solution_id)
        document = (
            self._checked_relation(
                "project.agile.solution.revision", values["document_revision_id"]
            )
            if values.get("document_revision_id")
            else self.env["project.agile.solution.revision"]
        )
        claim_records(document.document_id, allow_referencing=True)
        claim_records(document, allow_referencing=True)
        check_document(document, revision, revision.solution_id)
        existing = self.with_context(active_test=False).search(
            [("task_id", "=", task.id), ("requirement_revision_id", "=", revision.id)]
        )
        if existing:
            if not existing.active or existing.document_revision_id != document:
                raise ValidationError(
                    _(
                        "Retired or differently sourced coverage "
                        "requires a new deliberate revision."
                    )
                )
            return existing
        revision._seal()
        link = super().create(
            {
                **values,
                "active": True,
                "linked_by_id": self.env.uid,
                "linked_at": fields.Datetime.now(),
            }
        )

        task._record_solution_reference(link)
        return link

    # Coverage identity is immutable; retirement uses its dedicated action.
    def write(self, values):  # pylint: disable=method-required-super
        self._trace_authority()
        raise ValidationError(
            _(
                "Coverage identity is immutable; "
                "retire it with a reason and link the successor."
            )
        )

    # Traceability evidence must be retired rather than deleted.
    def unlink(self):  # pylint: disable=method-required-super
        self._trace_authority()
        raise ValidationError(  # pylint: disable=no-raise-unlink
            _("Retain traceability evidence; retire the working link instead.")
        )

    # Generic copy must not imply an authorized exact-work selection.
    def copy(self, default=None):  # pylint: disable=method-required-super
        raise ValidationError(_("Select exact native work explicitly."))

    def action_request_retirement(self):
        self.ensure_one()
        self._trace_authority()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.agile.requirement.task.retire.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_link_id": self.id},
        }

    def action_retire(self, reason):
        caller = self._trace_authority()
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise ValidationError(_("Give a bounded reason for retiring coverage."))
        with self.env.cr.savepoint():
            claim_records(caller.task_id, allow_referencing=True)
            claim_records(caller, allow_referencing=True)
            for link in caller:
                check_task(link.task_id, link.project_id, active=False)
                if link.active:
                    super(RequirementTaskLink, link).write(
                        {
                            "active": False,
                            "retired_by_id": self.env.uid,
                            "retired_at": fields.Datetime.now(),
                            "retirement_reason": reason.strip(),
                        }
                    )
                    link.task_id._record_solution_reference(link)
        return True


# Keep the established action/edge boundary colocated; structural moves are out.
# pylint: disable-next=no-wizard-in-models
class RequirementTaskRetireWizard(models.TransientModel):
    _name = "project.agile.requirement.task.retire.wizard"
    _description = "Retire Exact Working Coverage With a Reason"

    link_id = fields.Many2one(
        "project.agile.requirement.task.link", required=True, ondelete="restrict"
    )
    reason = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        self.sudo(False).check_access("write")
        return self.link_id.sudo(False).action_retire(self.reason)

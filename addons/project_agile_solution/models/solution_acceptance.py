"""Append-only explicit acceptance bound to exact approved intent and authority."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from odoo.addons.project_agile.utils import claim_records

INPUT = frozenset(
    {
        "requirement_revision_id",
        "document_revision_id",
        "decision",
        "authority_label",
        "criteria_evaluated",
        "evidence",
    }
)


class RequirementAcceptance(models.Model):
    _name = "project.agile.requirement.acceptance"
    _inherit = "project.agile.solution.access"
    _description = "Explicit Exact Requirement Acceptance Event"
    _check_company_auto = True
    _order = "id desc"
    _rec_name = "authority_label"

    requirement_revision_id = fields.Many2one(
        "project.agile.requirement.revision",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    document_revision_id = fields.Many2one(
        "project.agile.solution.revision",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    solution_id = fields.Many2one(
        related="requirement_revision_id.solution_id", store=True, index=True
    )
    decision = fields.Selection(
        [
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("withdrawn", "Withdrawn"),
        ],
        required=True,
    )
    authority_label = fields.Char(
        required=True,
        help=(
            "Named authority/role asserted by the exact baseline approver; "
            "not external authentication or legal signature."
        ),
    )
    criteria_evaluated = fields.Text(required=True)
    evidence = fields.Text(
        required=True,
        help=(
            "Manual observation/reference; displayed as text, "
            "never fetched, linked or treated as verified URL truth."
        ),
    )
    recorded_by_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict", copy=False
    )
    recorded_by_label = fields.Char(required=True, readonly=True, copy=False)
    recorded_at = fields.Datetime(required=True, readonly=True, copy=False)
    supersedes_id = fields.Many2one(
        "project.agile.requirement.acceptance",
        readonly=True,
        ondelete="restrict",
        copy=False,
    )

    @api.model
    def default_get(self, names):
        return {
            key: value
            for key, value in super()
            .default_get([name for name in names if name in INPUT])
            .items()
            if key in INPUT
        }

    def _search_native_project_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        requirements = (
            self.env["project.agile.requirement.revision"]
            .sudo(False)
            .with_context(active_test=False)
        )
        documents = (
            self.env["project.agile.solution.revision"]
            .sudo(False)
            .with_context(active_test=False)
        )
        accessible = Domain.AND(
            [
                Domain("requirement_revision_id", "in", requirements._search([])),
                Domain("document_revision_id", "in", documents._search([])),
            ]
        )
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    @api.model_create_multi
    # Delegation occurs in _append_event after exact-revision authorization.
    def create(self, vals_list):  # pylint: disable=method-required-super
        caller = self.sudo(False)
        caller.check_access("create")
        clean_context = {
            key: value
            for key, value in caller.env.context.items()
            if not key.startswith("default_")
        }
        # Replacement strips default_*; merging would restore forged identity.
        # pylint: disable-next=context-overridden
        caller = caller.with_context(clean_context)
        result = caller.browse()
        with self.env.cr.savepoint():
            for values in vals_list:
                result |= caller._append_event(values)
        return result

    def _append_event(self, values):
        if set(values) - INPUT:
            raise ValidationError(
                _("Acceptance identity, recorder, time and history are server managed.")
            )
        self._validate_evidence(values)
        requirement = self._checked_relation(
            "project.agile.requirement.revision", values.get("requirement_revision_id")
        )
        baseline = self._checked_relation(
            "project.agile.solution.revision", values.get("document_revision_id")
        )
        baseline._check_authority()
        claim_records(baseline.document_id, allow_referencing=True)
        claim_records(baseline, allow_referencing=True)
        claim_records(requirement, allow_referencing=True)
        self._check_decision_scope(requirement, baseline, values["decision"])
        previous = self.search(
            [
                ("requirement_revision_id", "=", requirement.id),
                ("document_revision_id", "=", baseline.id),
            ],
            limit=1,
        )
        if self.sudo().search_count(
            [
                ("requirement_revision_id", "=", requirement.id),
                ("document_revision_id", "=", baseline.id),
            ]
        ) != self.search_count(
            [
                ("requirement_revision_id", "=", requirement.id),
                ("document_revision_id", "=", baseline.id),
            ]
        ):
            raise AccessError(
                _("Required acceptance history is unavailable under current access.")
            )
        if values["decision"] == "withdrawn" and (
            not previous or previous.decision != "accepted"
        ):
            raise ValidationError(
                _(
                    "Withdraw only a currently accepted "
                    "exact requirement/baseline decision."
                )
            )
        requirement._seal()
        prepared = {
            **values,
            "recorded_by_id": self.env.uid,
            "recorded_by_label": self.env.user.display_name,
            "recorded_at": fields.Datetime.now(),
            "supersedes_id": previous.id or False,
        }
        event = super().create(prepared)
        requirement._record_acceptance(event)
        return event

    def _validate_evidence(self, values):
        if values.get("decision") not in ("accepted", "rejected", "withdrawn"):
            raise ValidationError(_("Choose an explicit acceptance decision."))
        for name, limit in (
            ("authority_label", 200),
            ("criteria_evaluated", 10000),
            ("evidence", 10000),
        ):
            value = values.get(name)
            if type(value) is not str or not value.strip() or len(value) > limit:
                raise ValidationError(
                    _(
                        "Record bounded authority, evaluated criteria "
                        "and nonempty manual evidence."
                    )
                )

    def _check_decision_scope(self, requirement, baseline, decision):
        baseline._render_payload()
        requirement.sudo(False).check_access("read")
        requirement.requirement_id.sudo(False).check_access("read")
        allowed_states = (
            ("approved",) if decision == "accepted" else ("approved", "superseded")
        )
        if (
            baseline.kind != "spec"
            or baseline.state not in allowed_states
            or baseline.solution_id != requirement.solution_id
            or requirement not in baseline.requirement_revision_ids
        ):
            raise ValidationError(
                _(
                    "Acceptance requires the exact requirement "
                    "in its currently approved specification baseline."
                )
            )
        if self.env.user != baseline.approved_by_id or not self.env.user.active:
            raise AccessError(
                _(
                    "Only the exact baseline approving authority "
                    "may record this decision."
                )
            )
        if (
            requirement.company_id
            and requirement.company_id not in self.env.user.company_ids
        ):
            raise AccessError(_("Current Project company membership is required."))

    def _check_event_read(self):
        caller = self._origin.sudo(False).with_context(active_test=False)
        if caller.search_count([("id", "in", caller.ids)]) != len(caller):
            raise AccessError(
                _("Exact acceptance context is unavailable under current access.")
            )
        caller.recorded_by_id.check_access("read")
        previous = caller.supersedes_id
        if previous.search_count([("id", "in", previous.ids)]) != len(previous):
            raise AccessError(
                _("Exact acceptance context is unavailable under current access.")
            )
        for baseline in caller.document_revision_id:
            baseline._render_payload()

    def read(self, fields=None, load="_classic_read"):
        self._check_event_read()
        return super().read(fields, load=load)

    def export_data(self, fields_to_export):
        self._check_event_read()
        return super().export_data(fields_to_export)

    # Decisions are append-only; super would rewrite acceptance evidence.
    def write(self, values):  # pylint: disable=method-required-super
        self._check_authority()
        raise ValidationError(
            _("Append a new decision; acceptance evidence cannot be rewritten.")
        )

    # Retain history; rejection or withdrawal must be a new event.
    def unlink(self):  # pylint: disable=method-required-super
        self.sudo(False).check_access("unlink")
        raise ValidationError(  # pylint: disable=no-raise-unlink
            _("Retain acceptance history; append rejection or withdrawal.")
        )

    # Copying could imply authority for a different exact-revision decision.
    def copy(self, default=None):  # pylint: disable=method-required-super
        raise ValidationError(_("Record a deliberate exact-revision decision."))

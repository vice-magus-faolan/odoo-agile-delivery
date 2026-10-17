"""Finite versioned solution context: narrative, questions, decisions and roles."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.project_agile.utils import claim_records

from .solution_content import check_reference_commands, reference_command_ids

COMMON_CONTENT = frozenset(
    {"title", "audience", "sequence", "body", "affected_requirement_revision_ids"}
)
TYPED_CONTENT = {
    "section": frozenset(),
    "actor": frozenset({"business_role"}),
    "domain": frozenset(),
    "deliverable": frozenset({"evaluation_expectations"}),
    "question": frozenset(
        {
            "question",
            "owner_id",
            "external_owner",
            "planning_significance",
            "resolution_status",
            "resolution",
            "resolution_rationale",
            "resolved_by_id",
            "resolved_at",
            "spike_task_ids",
        }
    ),
    "decision": frozenset({"decision_context", "choice", "consequences"}),
}
RESOLUTION_AUDIT = frozenset(
    {
        "resolution_status",
        "resolution",
        "resolution_rationale",
        "resolved_by_id",
        "resolved_at",
    }
)


class SolutionContext(models.Model):
    _name = "project.agile.solution.context"
    _inherit = "project.agile.solution.content.identity"
    _description = "Stable Typed Solution Context Identity"
    _check_company_auto = True
    _order = "project_id, key, id"
    _key_prefix = "CTX-"
    _identity_field = "context_id"
    _revision_model = "project.agile.solution.context.revision"

    kind = fields.Selection(
        [(kind, kind.title()) for kind in TYPED_CONTENT],
        required=True,
        default="section",
    )
    revision_ids = fields.One2many(
        "project.agile.solution.context.revision",
        "context_id",
        readonly=True,
        copy=False,
    )
    _key_unique = models.Constraint(
        "UNIQUE(project_id, key)", "Context key must be unique within its Project."
    )


class SolutionContextRevision(models.Model):
    _name = "project.agile.solution.context.revision"
    _inherit = "project.agile.solution.content.revision"
    _description = "Exact Typed Solution Context Revision"
    _check_company_auto = True
    _order = "sequence, context_id, number desc"
    _rec_name = "title"
    _identity_field = "context_id"
    _identity_model = "project.agile.solution.context"
    _document_field = "context_revision_ids"
    _inverse_fields = frozenset({"document_revision_ids", "kind"})

    context_id = fields.Many2one(
        "project.agile.solution.context",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    solution_id = fields.Many2one(
        related="context_id.solution_id", store=True, index=True
    )
    kind = fields.Selection(related="context_id.kind")
    predecessor_id = fields.Many2one(
        "project.agile.solution.context.revision",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    sequence = fields.Integer(default=10)
    body = fields.Html(sanitize=True, sanitize_overridable=False)
    affected_requirement_revision_ids = fields.Many2many(
        "project.agile.requirement.revision",
        "solution_context_requirement_rel",
        "context_revision_id",
        "requirement_revision_id",
        check_company=True,
    )
    document_revision_ids = fields.Many2many(
        "project.agile.solution.revision",
        "solution_document_context_rel",
        "context_revision_id",
        "document_revision_id",
        readonly=True,
        copy=False,
    )
    business_role = fields.Text()
    evaluation_expectations = fields.Text()
    question = fields.Text()
    owner_id = fields.Many2one("res.users", ondelete="restrict")
    external_owner = fields.Char()
    planning_significance = fields.Selection(
        [
            ("informational", "Informational"),
            ("planning", "Affects Planning"),
            ("blocking", "Blocks Related Work"),
        ]
    )
    resolution_status = fields.Selection(
        [("open", "Open"), ("resolved", "Resolved")], readonly=True, copy=False
    )
    resolution = fields.Text(readonly=True, copy=False)
    resolution_rationale = fields.Text(readonly=True, copy=False)
    resolved_by_id = fields.Many2one(
        "res.users", readonly=True, copy=False, ondelete="restrict"
    )
    resolved_at = fields.Datetime(readonly=True, copy=False)
    spike_task_ids = fields.Many2many(
        "project.task",
        "solution_question_spike_rel",
        "context_revision_id",
        "task_id",
        check_company=True,
    )
    decision_context = fields.Text()
    choice = fields.Text()
    consequences = fields.Text()
    _number_unique = models.Constraint(
        "UNIQUE(context_id, number)", "Context revision number must be unique."
    )

    @api.model
    def default_get(self, names):
        protected = RESOLUTION_AUDIT | {
            "affected_requirement_revision_ids",
            "spike_task_ids",
        }
        values = super().default_get([name for name in names if name not in protected])
        for name in RESOLUTION_AUDIT | {
            "affected_requirement_revision_ids",
            "spike_task_ids",
        }:
            values.pop(name, None)
        return values

    def _create_content(self, values):
        if RESOLUTION_AUDIT & values.keys():
            raise ValidationError(
                _("Resolve a question with the explicit resolution action.")
            )
        context = self._checked_relation(self._identity_model, values.get("context_id"))
        prepared = dict(values)
        if context.kind == "question":
            prepared["resolution_status"] = "open"
        record = super()._create_content(prepared)
        record.spike_task_ids._record_solution_reference(record)
        return record

    def read(self, fields=None, load="_classic_read"):
        self.sudo(False).check_access("read")
        self._validate_content()
        return super().read(fields, load=load)

    def export_data(self, fields_to_export):
        self.sudo(False).check_access("read")
        self._validate_content()
        return super().export_data(fields_to_export)

    def _check_input(self, values):
        for name in ("affected_requirement_revision_ids", "spike_task_ids"):
            if name in values:
                check_reference_commands(values[name])
        if values.get("owner_id"):
            self._checked_relation("res.users", values["owner_id"])
        if values.get("spike_task_ids"):
            task_ids = [
                item
                for command in values["spike_task_ids"]
                for item in reference_command_ids(command)
            ]
            tasks = (
                self.env["project.task"]
                .sudo(False)
                .with_context(active_test=False)
                .browse(task_ids)
            )
            tasks.check_access("read")
            claim_records(tasks, allow_referencing=True)
        for record in self:
            foreign = (
                set(values)
                & set().union(*TYPED_CONTENT.values()) - TYPED_CONTENT[record.kind]
            )
            if foreign:
                raise ValidationError(
                    _("Use only fields appropriate to this context kind.")
                )

    def write(self, values):
        if RESOLUTION_AUDIT & values.keys():
            raise ValidationError(
                _(
                    "Resolution audit is action-only; "
                    "a changed answer needs a successor."
                )
            )
        with self.env.cr.savepoint():
            result = super().write(values)
            if "spike_task_ids" in values:
                for record in self:
                    record.spike_task_ids._record_solution_reference(record)
            return result

    # Validation is side-effect/error-only; super's value is not its API.
    def _validate_content(self):  # pylint: disable=missing-return
        super()._validate_content()
        for record in self:
            record._validate_typed_content()
            record._validate_requirements()
            record._validate_spikes()

    def _validate_typed_content(self):
        self.ensure_one()
        all_typed = set().union(*TYPED_CONTENT.values())
        if any(self[name] for name in all_typed - TYPED_CONTENT[self.kind]):
            raise ValidationError(
                _("Fields from another context kind are not allowed.")
            )
        required = {
            "actor": ("business_role",),
            "deliverable": ("evaluation_expectations",),
            "question": ("question", "planning_significance", "owner_id"),
            "decision": ("decision_context", "choice", "consequences"),
        }.get(self.kind, ())
        for name in required:
            value = self[name]
            if not value or isinstance(value, str) and not value.strip():
                raise ValidationError(
                    _(
                        "Complete the required typed context, "
                        "ownership and evaluation fields."
                    )
                )
        if self.kind == "question":
            self._check_owner()

    def _check_owner(self):
        owner = self.owner_id.sudo(False)
        owner.check_access("read")
        # After caller-visible owner authorization, inspect only membership in
        # this already-authorized company. Never fetch/expose unrelated companies.
        company_allowed = not self.company_id or bool(
            owner.sudo().search_count(
                [("id", "=", owner.id), ("company_ids", "in", self.company_id.ids)]
            )
        )
        if not self.sealed and (not owner.active or owner.share or not company_allowed):
            raise ValidationError(
                _(
                    "Question owner must be an active internal user "
                    "in the Project company."
                )
            )

    def _validate_requirements(self):
        self.ensure_one()
        requirements = self.affected_requirement_revision_ids.sudo(False)
        requirements.check_access("read")
        total = (
            self.env["project.agile.requirement.revision"]
            .sudo()
            .search_count([("context_revision_ids", "in", self.ids)])
        )
        if len(requirements) != total:
            raise AccessError(
                _("Affected requirement context is unavailable under current access.")
            )
        requirements._validate_content()
        if any(row.solution_id != self.solution_id for row in requirements):
            raise ValidationError(
                _("Affected requirements must belong to this same solution.")
            )

    def _validate_spikes(self):
        self.ensure_one()
        tasks = self.spike_task_ids.sudo(False).with_context(active_test=False)
        tasks.check_access("read")
        total = (
            self.env["project.task"]
            .sudo()
            .with_context(active_test=False)
            .search_count([("solution_question_revision_ids", "in", self.ids)])
        )
        if len(tasks) != total:
            raise AccessError(_("Discovery work is unavailable under current access."))
        for task in tasks:
            if (
                task.project_id != self.project_id
                or task.agile_item_type_id.code != "spike"
            ):
                raise ValidationError(
                    _(
                        "Discovery links require existing "
                        "same-Project Agile Spike Tasks."
                    )
                )
            if not self.sealed and (not task.active or not task.project_id.active):
                raise ValidationError(
                    _("Select active discovery work for new context.")
                )

    def action_resolve(self, resolution, rationale):
        self.ensure_one()
        self._check_editable()
        if self.kind != "question" or self.resolution_status != "open":
            raise ValidationError(_("Resolve only an open working question."))
        if any(
            type(value) is not str or not value.strip() or len(value) > 10000
            for value in (resolution, rationale)
        ):
            raise ValidationError(_("Supply a bounded resolution and its rationale."))
        with self.env.cr.savepoint():
            # Bypass only this action-only field gate, not caller authority or seal.
            result = super().write(
                {
                    "resolution_status": "resolved",
                    "resolution": resolution.strip(),
                    "resolution_rationale": rationale.strip(),
                    "resolved_by_id": self.env.user.id,
                    "resolved_at": fields.Datetime.now(),
                }
            )
        return result

    def action_request_resolution(self):
        self.ensure_one()
        self._check_editable()
        if self.kind != "question" or self.resolution_status != "open":
            raise ValidationError(_("Resolve only an open working question."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.agile.solution.question.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_context_revision_id": self.id},
        }

    def _seal(self):
        tasks = self.spike_task_ids.sudo(False).with_context(active_test=False)
        tasks.check_access("read")
        claim_records(tasks, allow_referencing=True)
        self.affected_requirement_revision_ids._seal()
        return super()._seal()

    def _copy_content_values(self):
        self._validate_content()
        values = {
            **super()._copy_content_values(),
            "sequence": self.sequence,
            "body": self.body or "",
            "affected_requirement_revision_ids": [
                (6, 0, self.affected_requirement_revision_ids.ids)
            ],
        }
        for name in TYPED_CONTENT[self.kind] - RESOLUTION_AUDIT:
            values[name] = (
                [(6, 0, self.spike_task_ids.ids)]
                if name == "spike_task_ids"
                else self[name].id
                if name == "owner_id"
                else self[name]
            )
        return values

    def _snapshot_values(self):
        values = super()._snapshot_values()
        values.update(
            kind=self.kind,
            affected_requirements=[
                row._snapshot_values()
                for row in self.affected_requirement_revision_ids.sorted("id")
            ],
        )
        values.pop("affected_requirement_revision_ids", None)
        if self.kind == "question":
            values.pop("spike_task_ids", None)
            values.update(
                owner_label=self.owner_id.display_name,
                resolution_status=self.resolution_status,
                resolution=self.resolution or "",
                resolution_rationale=self.resolution_rationale or "",
                resolved_by_id=self.resolved_by_id.id or None,
                resolved_by_label=self.resolved_by_id.display_name or "",
                resolved_at=fields.Datetime.to_string(self.resolved_at)
                if self.resolved_at
                else None,
                spikes=[
                    {"task_id": task.id, "key": task.agile_key, "title": task.name}
                    for task in self.spike_task_ids.sorted("id")
                ],
            )
        return values

    # Closure validation returns no data; failures raise before projection.
    def _check_snapshot_reference(self, payload):  # pylint: disable=missing-return
        super()._check_snapshot_reference(payload)
        for values in payload["affected_requirements"]:
            self.env["project.agile.requirement.revision"].browse(
                values["revision_id"]
            )._check_snapshot_reference(values)
        for values in payload.get("spikes", []):
            task = (
                self.env["project.task"]
                .sudo(False)
                .with_context(active_test=False)
                .browse(values["task_id"])
            )
            task.check_access("read")
            if not task.exists():
                raise AccessError(
                    _(
                        "The exact discovery context is unavailable "
                        "under current access."
                    )
                )
        if payload.get("owner_id"):
            self.env["res.users"].sudo(False).browse(payload["owner_id"]).check_access(
                "read"
            )
        if payload.get("resolved_by_id"):
            self.env["res.users"].sudo(False).browse(
                payload["resolved_by_id"]
            ).check_access("read")

"""Immutable review/baseline content and action-only lifecycle transitions."""

import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .project_agile_solution import check_history_defaults

LIFECYCLE_FIELDS = frozenset(
    {
        "state",
        "number",
        "predecessor_id",
        "snapshot_json",
        "snapshot_sha256",
        "_snapshot_content",
        "_snapshot_digest",
        "submitted_by_id",
        "submitted_at",
        "approved_by_id",
        "approved_by_label",
        "approved_at",
        "superseded_by_id",
        "return_reason",
        "template_snapshot",
        "_template_content",
        "_narrative_version",
    }
)
SCOPE_FIELDS = frozenset({"document_id", "solution_id", "project_id", "company_id"})


class SolutionRevision(models.Model):
    _name = "project.agile.solution.revision"
    _inherit = "project.agile.solution.access"
    _description = "Solution Document Revision"
    _check_company_auto = True
    _order = "document_id, number desc, id desc"
    _rec_name = "title"

    _narrative_version = fields.Integer(
        readonly=True,
        copy=False,
        groups="project_agile_solution.group_snapshot_storage",
        help=(
            "Advanced by narrative section changes to conflict with concurrent "
            "submission and stale previews."
        ),
    )

    def _record_narrative_change(self):
        for record in self:
            super(SolutionRevision, record.sudo()).write(
                {
                    "_narrative_version": record.sudo()._narrative_version + 1,
                }
            )

        return True

    document_id = fields.Many2one(
        "project.agile.solution.document",
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
        copy=False,
    )
    solution_id = fields.Many2one(
        related="document_id.solution_id", store=True, index=True
    )
    kind = fields.Selection(related="document_id.kind")
    title = fields.Char(required=True)
    active = fields.Boolean(default=True)
    number = fields.Integer(required=True, readonly=True, copy=False)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "In Review"),
            ("approved", "Approved"),
            ("superseded", "Superseded"),
        ],
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )
    predecessor_id = fields.Many2one(
        "project.agile.solution.revision",
        readonly=True,
        ondelete="restrict",
        copy=False,
    )
    section_ids = fields.One2many(
        "project.agile.solution.section", "revision_id", copy=False
    )
    based_sow_revision_id = fields.Many2one(
        "project.agile.solution.revision", ondelete="restrict", check_company=True
    )
    scope_disposition = fields.Selection(
        [("within", "Within Existing Scope"), ("change", "Explicit Scope Change")],
        default="within",
        required=True,
    )
    scope_change_reason = fields.Text()
    snapshot_json = fields.Text(compute="_compute_checked_snapshot", compute_sudo=False)
    snapshot_sha256 = fields.Char(
        compute="_compute_checked_snapshot", compute_sudo=False
    )
    # This unassigned, non-implied group is a storage boundary, not a user role.
    # Technical Features becomes effective in debug; only checked narrow sudo
    # retrieval may expose storage through the current-caller projections below.
    _snapshot_content = fields.Text(
        readonly=True,
        copy=False,
        groups="project_agile_solution.group_snapshot_storage",
    )
    _snapshot_digest = fields.Char(
        readonly=True,
        copy=False,
        groups="project_agile_solution.group_snapshot_storage",
    )
    template_snapshot = fields.Text(
        compute="_compute_checked_template", compute_sudo=False
    )
    _template_content = fields.Text(
        readonly=True,
        copy=False,
        groups="project_agile_solution.group_snapshot_storage",
    )
    submitted_by_id = fields.Many2one(
        "res.users", readonly=True, ondelete="restrict", copy=False
    )
    submitted_at = fields.Datetime(readonly=True, copy=False)
    approved_by_id = fields.Many2one(
        "res.users", readonly=True, ondelete="restrict", copy=False
    )
    approved_by_label = fields.Char(readonly=True, copy=False)
    approved_at = fields.Datetime(readonly=True, copy=False)
    superseded_by_id = fields.Many2one(
        "project.agile.solution.revision",
        readonly=True,
        ondelete="restrict",
        copy=False,
    )
    return_reason = fields.Text(readonly=True, copy=False)

    _number_unique = models.Constraint(
        "UNIQUE(document_id, number)", "Document revision number must be unique."
    )

    @api.model
    def default_get(self, names):
        values = super().default_get(names)
        for name in LIFECYCLE_FIELDS | {"solution_id", "project_id", "company_id"}:
            values.pop(name, None)
        return values

    @api.model_create_multi
    # _create_draft delegates after scope, numbering and lifecycle checks.
    def create(self, vals_list):  # pylint: disable=method-required-super
        self.sudo(False).check_access("create")
        records = self.browse()
        # Batch savepoint makes direct Python callers atomic too, not only RPC.
        with self.env.cr.savepoint():
            for values in vals_list:
                records |= self._create_draft(values)
        return records

    def _create_draft(self, values):
        values = dict(values)
        if (
            LIFECYCLE_FIELDS | {"solution_id", "project_id", "company_id", "kind"}
        ) & values.keys():
            raise ValidationError(
                _("Revision identity, lifecycle and audit fields are server managed.")
            )
        if values.get("based_sow_revision_id"):
            self._checked_relation(self._name, values["based_sow_revision_id"])
        document = self._checked_relation(
            "project.agile.solution.document", values.get("document_id")
        )
        document._check_authority()
        document.solution_id.lock_for_update()
        document.lock_for_update()
        self._check_active_document(document)
        revisions = document._complete_revisions()
        if revisions and revisions[-1].state in ("draft", "review"):
            raise ValidationError(
                _("A working revision already exists. Open it instead.")
            )
        predecessor = revisions[-1] if revisions else self.browse()
        values.update(
            document_id=document.id,
            number=predecessor.number + 1 if predecessor else 1,
            predecessor_id=predecessor.id or False,
            state="draft",
        )
        check_history_defaults(self.env)
        revision = super().create(values)
        revision._validate_content()
        document._record_revision(revision)
        return revision

    def _check_active_document(self, document):
        document.project_id.lock_for_update()
        document.solution_id.lock_for_update()
        if (
            not document.active
            or not document.solution_id.active
            or not document.project_id.active
            or not document.project_id.agile_enabled
        ):
            raise ValidationError(
                _("Select an active document in an active Agile solution.")
            )

    def _check_editable(self):
        self._check_authority()
        self.document_id.lock_for_update()
        self.lock_for_update()
        if any(record.state != "draft" for record in self):
            raise ValidationError(
                _(
                    "Review and historical content are immutable. "
                    "Return review explicitly or create a successor."
                )
            )

    def write(self, values):
        self._check_editable()
        if (LIFECYCLE_FIELDS | SCOPE_FIELDS | {"kind"}) & values.keys():
            raise ValidationError(
                _(
                    "Use explicit lifecycle actions; "
                    "revision identity and audit cannot be written."
                )
            )
        if values.get("based_sow_revision_id"):
            self._checked_relation(self._name, values["based_sow_revision_id"])
        with self.env.cr.savepoint():
            result = super().write(values)
            self._validate_content()
        return result

    def unlink(self):
        self._check_editable()
        with self.env.cr.savepoint():
            self.section_ids.unlink()
            return super().unlink()

    # Only New Revision may derive a numbered successor.
    def copy(self, default=None):  # pylint: disable=method-required-super
        raise ValidationError(
            _("Create a numbered working successor with New Revision, not Copy.")
        )

    def _validate_content(self):
        """Extension boundary: later exact requirement/context members validate here."""
        for record in self:
            sow = record.based_sow_revision_id
            if sow:
                sow.sudo(False).check_access("read")
                if (
                    sow.kind != "sow"
                    or sow.solution_id != record.solution_id
                    or record.kind != "spec"
                ):
                    raise ValidationError(
                        _(
                            "A spec may reference only a SOW revision "
                            "in the same solution."
                        )
                    )
            if (
                record.scope_disposition == "change"
                and not (record.scope_change_reason or "").strip()
            ):
                raise ValidationError(_("Record an explicit scope-change rationale."))
            record.section_ids.sudo(False).check_access("read")
            total = (
                record.env["project.agile.solution.section"]
                .sudo()
                .search_count([("revision_id", "=", record.id)])
            )
            if total != len(record.section_ids):
                raise AccessError(
                    _("Required narrative content is unavailable under current access.")
                )

    @api.depends("_snapshot_content", "_snapshot_digest")
    @api.depends_context("uid")
    def _compute_checked_snapshot(self):
        """Public reads/exports never return sealed text without current closure
        access.
        """
        for record in self:
            caller = record.sudo(False)
            caller.check_access("read")
            # Narrow payload retrieval follows parent authority; stored pointers
            # are not authority and their complete closure is checked as caller.
            raw = record.sudo()._snapshot_content
            if raw:
                caller._check_snapshot_closure(json.loads(raw))
            record.snapshot_json = raw
            record.snapshot_sha256 = record.sudo()._snapshot_digest

    def action_read_snapshot(self):
        """Exact native/RPC read API; recheck closure even after a cached prior read."""
        self.ensure_one()
        self.sudo(False).check_access("read")
        self.invalidate_recordset(["snapshot_json", "snapshot_sha256"])
        return {
            "snapshot_json": self.snapshot_json,
            "snapshot_sha256": self.snapshot_sha256,
            "state": self.state,
            "number": self.number,
        }

    @api.depends("_template_content")
    @api.depends_context("uid")
    def _compute_checked_template(self):
        for record in self:
            caller = record.sudo(False)
            caller.check_access("read")
            caller._validate_content()
            record.template_snapshot = record.sudo()._template_content

    def read(self, fields=None, load="_classic_read"):
        self.invalidate_recordset(
            ["snapshot_json", "snapshot_sha256", "template_snapshot"]
        )
        return super().read(fields, load=load)

    def export_data(self, fields_to_export):
        self.invalidate_recordset(
            ["snapshot_json", "snapshot_sha256", "template_snapshot"]
        )
        return super().export_data(fields_to_export)

    def _check_snapshot_closure(self, payload):
        self.document_id.check_access("read")
        self.solution_id.check_access("read")
        self.project_id.check_access("read")
        ids = [section["section_id"] for section in payload["sections"]]
        sections = self.env["project.agile.solution.section"].browse(ids)
        sections.check_access("read")
        if len(sections.exists()) != len(ids):
            raise AccessError(
                _("The exact baseline is unavailable under current access.")
            )
        sow_id = payload.get("based_sow_revision_id")
        if sow_id:
            sow = self.env[self._name].browse(sow_id)
            sow.check_access("read")
            if not sow.exists():
                raise AccessError(
                    _("The exact baseline is unavailable under current access.")
                )
            sow._check_snapshot_closure(payload["based_sow_content"])

    def _snapshot_payload(self):
        """Store actual ordered sanitized content; live labels are navigation only.

        Extensions add actual exact-revision content and identity provenance here,
        after their own current-user closure checks; never mutable-pointer text.
        """
        self.ensure_one()
        self._validate_content()
        return {
            "schema_version": 1,
            "document_id": self.document_id.id,
            "revision_id": self.id,
            "number": self.number,
            "document_name": self.document_id.name,
            "kind": self.kind,
            "solution_id": self.solution_id.id,
            "solution_name": self.solution_id.name,
            "project_id": self.project_id.id,
            "project_name": self.project_id.name,
            "scope_disposition": self.scope_disposition,
            "scope_change_reason": self.scope_change_reason or "",
            "based_sow_revision_id": self.based_sow_revision_id.id or None,
            "based_sow_snapshot_sha256": self.based_sow_revision_id.snapshot_sha256
            or None,
            "based_sow_content": (
                json.loads(self.based_sow_revision_id.snapshot_json)
                if self.based_sow_revision_id.snapshot_json
                else self.based_sow_revision_id._snapshot_payload()
            )
            if self.based_sow_revision_id
            else None,
            "template_provenance": self.template_snapshot or None,
            "title": self.title,
            "sections": [
                section._snapshot_values()
                for section in self.section_ids.sorted(lambda s: (s.sequence, s.id))
            ],
        }

    def _transition_caller(self, expected):
        self.ensure_one()
        caller = self._check_authority()
        self.document_id.lock_for_update()
        self.lock_for_update()
        caller._check_active_document(caller.document_id)
        if self.state != expected:
            raise ValidationError(
                _("The revision state changed; reopen the current revision.")
            )
        return caller

    def action_submit(self):
        caller = self._transition_caller("draft")
        payload = json.dumps(
            caller._snapshot_payload(), ensure_ascii=False, sort_keys=True
        )
        super(SolutionRevision, self.sudo()).write(
            {
                "state": "review",
                "_snapshot_content": payload,
                "_snapshot_digest": hashlib.sha256(payload.encode()).hexdigest(),
                "submitted_by_id": caller.env.user.id,
                "submitted_at": fields.Datetime.now(),
            }
        )
        return True

    def action_return_to_draft(self, reason=None):
        self._transition_caller("review")
        if type(reason) is not str or not reason.strip() or len(reason) > 4000:
            raise ValidationError(_("Supply a bounded, nonempty return reason."))
        super(SolutionRevision, self.sudo()).write(
            {
                "state": "draft",
                "return_reason": reason.strip(),
                "_snapshot_content": False,
                "_snapshot_digest": False,
            }
        )
        return True

    def _check_sow_approval(self):
        """Separate approvals; explicit expansion needs an approved changed SOW."""
        if self.kind != "spec":
            return
        documents = (
            self.env["project.agile.solution.document"]
            .with_context(active_test=False)
            .search([("solution_id", "=", self.solution_id.id), ("kind", "=", "sow")])
        )
        total = (
            self.env["project.agile.solution.document"]
            .sudo()
            .with_context(active_test=False)
            .search_count(
                [("solution_id", "=", self.solution_id.id), ("kind", "=", "sow")]
            )
        )
        if total != len(documents):
            raise AccessError(
                _("Required scope information is unavailable under current access.")
            )
        if not documents:
            return  # An internal product initiative never requires a customer SOW.
        sow = self.based_sow_revision_id
        if not sow or sow.state != "approved":
            raise ValidationError(
                _("Separately approve and select the current SOW baseline first.")
            )
        sow.sudo(False).check_access("read")
        submitted = json.loads(self.snapshot_json)
        if submitted["based_sow_content"] != json.loads(sow.snapshot_json):
            raise ValidationError(
                _(
                    "The referenced SOW content changed during review; "
                    "return and submit this spec again."
                )
            )
        if self.scope_disposition == "change":
            previous_sow = self.predecessor_id.based_sow_revision_id
            if (
                sow.scope_disposition != "change"
                or not sow.scope_change_reason
                or (
                    previous_sow
                    and (
                        sow.document_id != previous_sow.document_id
                        or sow.number <= previous_sow.number
                    )
                )
            ):
                raise ValidationError(
                    _(
                        "Expanded spec scope needs an explicitly approved "
                        "successor SOW change."
                    )
                )

    def action_approve(self):
        caller = self._transition_caller("review")
        approver = caller.document_id.approver_id
        caller.document_id._check_approver()
        if approver != caller.env.user:
            raise AccessError(
                _(
                    "Only the explicitly designated current approver "
                    "can approve this document."
                )
            )
        caller._validate_content()
        caller._check_sow_approval()
        predecessor = caller.predecessor_id
        if predecessor and predecessor.state != "approved":
            raise ValidationError(
                _("The predecessor baseline is stale; reopen the current document.")
            )
        with self.env.cr.savepoint():
            caller.solution_id._record_approval(caller)
            if predecessor:
                super(SolutionRevision, predecessor).write(
                    {"state": "superseded", "superseded_by_id": self.id}
                )
            super().write(
                {
                    "state": "approved",
                    "approved_by_id": caller.env.user.id,
                    "approved_by_label": caller.env.user.display_name,
                    "approved_at": fields.Datetime.now(),
                }
            )
        return True

    def action_new_revision(self):
        caller = self._check_authority()
        self.ensure_one()
        self.document_id.lock_for_update()
        self.lock_for_update()
        if self.state not in ("approved", "superseded"):
            raise ValidationError(
                _("A working successor starts from an approved baseline.")
            )
        latest = self.document_id._complete_revisions()[-1]
        if latest != self:
            raise ValidationError(
                _("Create the successor from the current baseline only.")
            )
        caller._validate_content()
        values = {
            "document_id": self.document_id.id,
            "title": self.title,
            "based_sow_revision_id": self.based_sow_revision_id.id or False,
            "scope_disposition": "within",
            "section_ids": [
                (0, 0, section._copy_values()) for section in caller.section_ids
            ],
        }
        successor = self.env[self._name].create(values)
        if self.template_snapshot:
            super(SolutionRevision, successor.sudo()).write(
                {"_template_content": self.template_snapshot}
            )
        return successor._form_action()

    def _form_action(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_apply_template(self, template_id):
        self.ensure_one()
        self._check_editable()
        template = self._checked_relation(
            "project.agile.solution.template", template_id
        )
        if (
            not template.active
            or template.kind != self.kind
            or (template.company_id and template.company_id != self.company_id)
        ):
            raise ValidationError(
                _("Select an active compatible template in the document company.")
            )
        sections = template._validated_sections()
        with self.env.cr.savepoint():
            self.write({"section_ids": [(0, 0, values) for values in sections]})
            provenance = json.dumps(
                {
                    "id": template.id,
                    "name": template.name,
                    "version": template.version,
                    "sections": sections,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            super(SolutionRevision, self.sudo()).write(
                {"_template_content": provenance}
            )
        return True

    def action_request_return(self):
        self._transition_caller("review")
        return self._wizard_action("return")

    def action_request_template(self):
        self.ensure_one()
        self._check_editable()
        return self._wizard_action("template")

    def _wizard_action(self, operation):
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.agile.solution.revision.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_revision_id": self.id, "default_operation": operation},
        }

"""Creator-owned bounded preview and atomic retry-safe deliberate confirmation."""

import hashlib
import json
from uuid import uuid4

from markupsafe import Markup, escape

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from odoo.addons.project_agile.utils import claim_records

from .solution_content import check_reference_commands
from .solution_task_access import (
    check_document,
    check_requirements,
    check_task,
)

INPUT = frozenset(
    {
        "solution_id",
        "operation",
        "name",
        "description",
        "agile_item_type_id",
        "task_id",
        "document_revision_id",
        "requirement_revision_ids",
        "copy_acceptance_expectations",
    }
)


class SolutionTaskIntent(models.Model):
    _name = "project.agile.solution.task.intent"
    _inherit = "project.agile.solution.task.access"
    _description = "Deliberate Native Task Preview and Confirmation"
    _check_company_auto = True
    _order = "id desc"

    solution_id = fields.Many2one(
        "project.agile.solution", required=True, ondelete="restrict", check_company=True
    )
    operation = fields.Selection(
        [("create", "Create Native Task"), ("link", "Link Existing Native Task")],
        required=True,
        default="link",
    )
    name = fields.Char(required=True)
    description = fields.Html()
    copy_acceptance_expectations = fields.Boolean(
        default=False,
        help="Copy the selected exact expectations into editable Task criteria.",
    )
    acceptance_criteria_preview = fields.Html(
        string="Task Acceptance Criteria Preview",
        compute="_compute_acceptance_criteria_preview",
        compute_sudo=False,
    )
    agile_item_type_id = fields.Many2one("project.agile.item.type", ondelete="restrict")
    task_id = fields.Many2one(
        "project.task", readonly=True, ondelete="restrict", check_company=True
    )
    document_revision_id = fields.Many2one(
        "project.agile.solution.revision", ondelete="restrict", check_company=True
    )
    requirement_revision_ids = fields.Many2many(
        "project.agile.requirement.revision",
        "solution_intent_requirement_rel",
        "intent_id",
        "requirement_revision_id",
        readonly=True,
        check_company=True,
    )
    creator_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict"
    )
    token = fields.Char(required=True, readonly=True, copy=False)
    state = fields.Selection(
        [("preview", "Previewed, Unconfirmed"), ("consumed", "Confirmed")],
        required=True,
        default="preview",
        readonly=True,
    )
    consumed_at = fields.Datetime(readonly=True)
    _source_digest = fields.Char(
        readonly=True, groups="project_agile_solution.group_snapshot_storage"
    )
    preview_text = fields.Text(compute="_compute_preview_text", compute_sudo=False)
    _token_unique = models.Constraint(
        "UNIQUE(token)", "Preview identity must be unique."
    )

    @api.model
    def default_get(self, names):
        values = {
            key: value
            for key, value in super()
            .default_get([name for name in names if name in INPUT])
            .items()
            if key in INPUT
        }
        if "state" in names:
            values["state"] = "preview"
        if "creator_id" in names:
            values["creator_id"] = self.env.uid
        if "copy_acceptance_expectations" in names:
            # An ambient context default is not a deliberate choice in this proposal.
            values["copy_acceptance_expectations"] = False
        return values

    @api.model_create_multi
    # _create_preview performs authorized delegation, not this public batch loop.
    def create(self, vals_list):  # pylint: disable=method-required-super
        caller = self.sudo(False)
        caller.check_access("create")
        records = caller.browse()
        with self.env.cr.savepoint():
            for values in vals_list:
                records |= caller._create_preview(values)
        return records

    def _create_preview(self, values):
        if set(values) - INPUT:
            raise ValidationError(
                _("Preview identity and consumption are server managed.")
            )
        solution = self._checked_relation(
            "project.agile.solution", values.get("solution_id")
        )
        solution.check_access("write")
        solution.project_id._check_agile_project_access()
        if not self.env.user.active or not (
            self.env.user.has_group("project.group_project_manager")
            or self.env.user.has_group("project_agile_solution.group_business_analyst")
        ):
            raise AccessError(_("An active Solution author must preview work."))
        commands = values.get("requirement_revision_ids", [])
        check_reference_commands(commands)
        if len(commands) == 1 and commands[0][0] == Command.SET:
            ids = commands[0][2]
        elif commands and all(command[0] == Command.LINK for command in commands):
            # Native many2many Form/web_save emits LINK, RPC commonly emits SET.
            ids = [command[1] for command in commands]
        else:
            raise ValidationError(
                _("Preview one explicit bounded set of exact revisions.")
            )
        if not 1 <= len(ids) <= 20 or len(set(ids)) != len(ids):
            raise ValidationError(
                _("Select between one and twenty distinct exact revisions.")
            )
        revisions = self.env["project.agile.requirement.revision"].browse(ids)
        check_requirements(revisions, solution)
        if values.get("operation", "link") == "link":
            task = self._checked_relation("project.task", values.get("task_id"))
            check_task(task, solution.project_id)
        values = {
            **values,
            "requirement_revision_ids": [Command.set(ids)],
            "copy_acceptance_expectations": values.get(
                "copy_acceptance_expectations", False
            ),
        }
        record = super().create(
            {
                **values,
                "creator_id": self.env.uid,
                "token": str(uuid4()),
                "state": "preview",
            }
        )
        record._validate_proposal()
        digest = record._fingerprint()
        super(SolutionTaskIntent, record.sudo()).write({"_source_digest": digest})
        return record

    def _validate_proposal(self):
        self.ensure_one()
        self._trace_authority()
        revisions = check_requirements(self.requirement_revision_ids, self.solution_id)
        if len(revisions.requirement_id) != len(revisions):
            raise ValidationError(
                _("Choose one exact revision per requirement identity.")
            )
        if (
            not isinstance(self.name, str)
            or not self.name.strip()
            or len(self.name) > 200
            or len(self.description or "") > 20000
        ):
            raise ValidationError(_("Use a meaningful bounded Task proposal."))
        check_document(self.document_revision_id, revisions, self.solution_id)
        if self.operation == "link":
            if self.copy_acceptance_expectations:
                raise ValidationError(
                    _("Copy expectations only when creating new native work.")
                )
            check_task(self.task_id, self.project_id)
        else:
            if self.task_id:
                raise ValidationError(
                    _("A creation preview cannot select an existing Task.")
                )
            self.env["project.task"].check_access("create")
            item_type = self.agile_item_type_id.sudo(False)
            item_type.check_access("read")
            if not item_type or not item_type.active:
                raise ValidationError(_("Select an active native Agile item type."))
        return revisions

    def _fingerprint(self):
        self.ensure_one()
        revisions = self.requirement_revision_ids
        values = {
            "revisions": [row._snapshot_values() for row in revisions.sorted("id")],
            "heads": [
                identity._complete_revisions()[-1].id
                for identity in revisions.requirement_id.sorted("id")
            ],
        }
        if self.document_revision_id:
            document = self.document_revision_id
            values["document"] = {
                "id": document.id,
                "content": document._snapshot_payload(),
                "heads": [
                    (row.id, row.number, row.state, str(row.write_date))
                    for row in document.document_id._complete_revisions()
                ],
            }
        return hashlib.sha256(
            json.dumps(values, sort_keys=True, default=str).encode()
        ).hexdigest()

    def _check_creator(self):
        caller = self._trace_authority()
        if any(record.creator_id != caller.env.user for record in caller):
            raise AccessError(
                _("Only the previewing current user can confirm this intent.")
            )
        return caller

    @api.depends_context("uid")
    def _compute_preview_text(self):
        for record in self:
            if not record._origin.id:
                record.preview_text = False
                continue
            record.sudo(False).check_access("read")
            revisions = check_requirements(
                record.requirement_revision_ids, record.solution_id, active=False
            )
            record.preview_text = "\n".join(
                f"{row.requirement_id.key} v{row.number}: {row.title}"
                for row in revisions.sorted("id")
            )

    @api.depends(
        "copy_acceptance_expectations", "requirement_revision_ids", "operation"
    )
    @api.depends_context("uid")
    def _compute_acceptance_criteria_preview(self):
        for record in self:
            record.acceptance_criteria_preview = False
            if (
                record.operation != "create"
                or not record.copy_acceptance_expectations
                or not record.requirement_revision_ids
            ):
                continue
            if record._origin.id:
                record._check_current_trace_read()
            revisions = check_requirements(
                record.requirement_revision_ids, record.solution_id, active=False
            )
            record.acceptance_criteria_preview = Markup("").join(
                Markup("<p>%s</p>")
                % escape(row.acceptance_expectations).replace("\n", Markup("<br>"))
                for row in revisions.sorted("id")
            )

    # Preview values cannot change after the user has inspected them.
    def write(self, values):  # pylint: disable=method-required-super
        self._check_creator()
        raise ValidationError(
            _(
                "Preview values are immutable; "
                "create a fresh preview for a changed proposal."
            )
        )

    # Retained intent identities provide stable idempotent retries.
    def unlink(self):  # pylint: disable=method-required-super
        self._check_creator()
        # pylint: disable=no-raise-unlink
        raise ValidationError(_("Keep preview and consumed retry identities."))

    # A copy cannot substitute for a fresh deliberate preview.
    def copy(self, default=None):  # pylint: disable=method-required-super
        raise ValidationError(
            _("Create a fresh explicit preview, not a copy of a retry identity.")
        )

    def action_request_confirmation(self):
        self.ensure_one()
        self._check_creator()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.agile.solution.task.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_intent_id": self.id},
        }

    def action_confirm(self):
        self.ensure_one()
        caller = self._check_creator()
        with self.env.cr.savepoint():
            claim_records(caller, allow_referencing=True)
            caller._check_creator()
            if caller.state == "consumed":
                check_task(
                    caller.task_id, caller.project_id, mutation=False, active=False
                )
                return caller._task_action()
            revisions = caller._validate_proposal()
            claim_records(caller.task_id, allow_referencing=True)
            claim_records(caller.project_id, allow_referencing=True)
            claim_records(caller.solution_id, allow_referencing=True)
            claim_records(revisions.requirement_id, allow_referencing=True)
            claim_records(revisions, allow_referencing=True)
            claim_records(
                caller.document_revision_id.document_id, allow_referencing=True
            )
            claim_records(caller.document_revision_id, allow_referencing=True)
            caller._validate_proposal()
            if caller._fingerprint() != caller.sudo()._source_digest:
                raise ValidationError(
                    _(
                        "Requirement or specification context changed; "
                        "preview again before confirming."
                    )
                )
            task = caller.task_id or caller._create_task()
            caller._link_task(task)
            super(SolutionTaskIntent, caller).write(
                {
                    "state": "consumed",
                    "task_id": task.id,
                    "consumed_at": fields.Datetime.now(),
                }
            )
            return caller._task_action()

    def _create_task(self):
        # Caller defaults, active IDs and workflow/context switches cannot add
        # hidden criteria, estimates, planning or other side effects to preview.
        context = {
            name: self.env.context[name]
            for name in ("allowed_company_ids", "lang", "tz")
            if name in self.env.context
        }
        return (
            # pylint: disable-next=context-overridden
            self.env["project.task"]
            # Replacement removes caller defaults and side-effect switches.
            .with_context(context)
            .create(
                {
                    "name": self.name,
                    "description": self.description,
                    "project_id": self.project_id.id,
                    "agile_item_type_id": self.agile_item_type_id.id,
                    "agile_acceptance_criteria": self.acceptance_criteria_preview
                    or False,
                }
            )
        )

    def _link_task(self, task):
        return self.env["project.agile.requirement.task.link"].create(
            [
                {
                    "task_id": task.id,
                    "requirement_revision_id": row.id,
                    "document_revision_id": self.document_revision_id.id or False,
                }
                for row in self.requirement_revision_ids
            ]
        )

    def _task_action(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "res_id": self.task_id.id,
            "view_mode": "form",
        }


# Preserve the existing colocated confirmation boundary; no module moves here.
# pylint: disable-next=no-wizard-in-models
class TaskConfirmWizard(models.TransientModel):
    _name = "project.agile.solution.task.confirm.wizard"
    _description = "Confirm Previewed Native Task Work"

    intent_id = fields.Many2one(
        "project.agile.solution.task.intent", required=True, ondelete="restrict"
    )
    preview_text = fields.Text(
        related="intent_id.preview_text", readonly=True, compute_sudo=False
    )
    name = fields.Char(related="intent_id.name", readonly=True, compute_sudo=False)
    description = fields.Html(
        related="intent_id.description", readonly=True, compute_sudo=False
    )
    copy_acceptance_expectations = fields.Boolean(
        related="intent_id.copy_acceptance_expectations",
        readonly=True,
        compute_sudo=False,
    )
    acceptance_criteria_preview = fields.Html(
        related="intent_id.acceptance_criteria_preview",
        readonly=True,
        compute_sudo=False,
    )
    operation = fields.Selection(
        related="intent_id.operation", readonly=True, compute_sudo=False
    )
    task_id = fields.Many2one(
        related="intent_id.task_id", readonly=True, compute_sudo=False
    )
    native_intent_access = fields.Boolean(
        compute="_compute_native_intent_access", search="_search_native_intent_access"
    )

    def _compute_native_intent_access(self):
        for wizard in self:
            wizard.native_intent_access = True

    def _search_native_intent_access(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        intents = self.env["project.agile.solution.task.intent"].sudo(False)
        accessible = Domain("intent_id", "in", intents._search([]))
        positive = Domain.OR(
            accessible if item is True else ~accessible
            for item in value
            if type(item) is bool
        )
        return positive if operator == "in" else ~positive

    @api.model
    def default_get(self, names):
        return super().default_get([name for name in names if name == "intent_id"])

    @api.model_create_multi
    def create(self, vals_list):
        caller = self.sudo(False)
        caller.check_access("create")
        values = []
        intents = caller.env["project.agile.solution.task.intent"]
        for proposal in vals_list:
            if set(proposal) - {"intent_id"}:
                raise ValidationError(
                    _(
                        "Confirmation projects an existing preview; "
                        "its values are not caller supplied."
                    )
                )
            intent_id = proposal.get(
                "intent_id", caller.default_get(["intent_id"]).get("intent_id")
            )
            intent = intents._checked_relation(
                "project.agile.solution.task.intent", intent_id
            )
            intent._check_current_trace_read()
            intent._check_creator()
            values.append({"intent_id": intent.id})
        return super(TaskConfirmWizard, caller).create(values)

    def _check_current_intent(self):
        """Transient ownership cannot grant authority over a related preview.

        Re-query persisted references before projection, even when related values
        were cached before a custom rule changed. Unsaved native Forms have only
        an origin, so no transient row or proposal is treated as authority.
        """
        caller = self._origin.sudo(False)
        caller.check_access("read")
        intents = caller.intent_id.sudo(False)
        intents._check_current_trace_read()
        intents._check_creator()
        return caller

    def read(self, fields=None, load="_classic_read"):
        self._check_current_intent()
        return super().read(fields, load)

    def export_data(self, fields_to_export):
        self._check_current_intent()
        return super().export_data(fields_to_export)

    # Confirmation is an immutable projection of the inspected intent.
    def write(self, values):  # pylint: disable=method-required-super
        self._check_current_intent()
        raise ValidationError(
            _("Confirmation selection is immutable; open a fresh confirmation.")
        )

    def action_confirm(self):
        self.ensure_one()
        self.sudo(False).check_access("write")
        return self._check_current_intent().intent_id.sudo(False).action_confirm()

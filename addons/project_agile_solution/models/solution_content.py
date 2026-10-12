"""Shared identity/revision mechanics for the two finite intent vocabularies."""

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .solution_access import lock_records

SCOPE = frozenset({"solution_id", "project_id", "company_id", "native_project_access"})
AUDIT = frozenset({"number", "predecessor_id", "sealed", "sealed_at", "sealed_by_id"})


def check_reference_commands(commands):
    """References select existing exact rows; never mutate them through an inverse."""
    if not isinstance(commands, (list, tuple)):
        raise ValidationError(_("Select existing exact revisions."))
    for command in commands:
        reference_command_ids(command)


def reference_command_ids(command):
    """Validate native/RPC reference tuples and return their literal selected IDs."""
    if not isinstance(command, (list, tuple)) or len(command) != 3:
        raise ValidationError(_("Use explicit reference commands."))
    operation, record_id, payload = command
    # Odoo 19's Python helpers emit Command IntEnum; RPC emits plain ints.
    if type(operation) not in (int, Command) or operation not in (3, 4, 5, 6):
        raise ValidationError(
            _("References cannot create, update or delete another record.")
        )
    if operation in (3, 4):
        ids = [record_id]
    else:
        if type(record_id) is not int or record_id != 0:
            raise ValidationError(_("Use canonical reference command IDs."))
        ids = payload if operation == 6 else []
    _check_reference_ids(ids)
    return ids


def _check_reference_ids(ids):
    if not isinstance(ids, (list, tuple)) or any(
        type(item) is not int or item <= 0 for item in ids
    ):
        raise ValidationError(_("Select available record IDs."))


class ContentIdentity(models.AbstractModel):
    _name = "project.agile.solution.content.identity"
    _inherit = "project.agile.solution.access"
    _description = "Stable Solution Content Identity Mechanics"

    name = fields.Char(required=True)
    key = fields.Char(required=True, readonly=True, copy=False, index=True)
    active = fields.Boolean(default=True)
    solution_id = fields.Many2one(
        "project.agile.solution",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )

    @api.model
    def default_get(self, names):
        values = super().default_get(
            [name for name in names if name not in {"key", "revision_ids"}]
        )
        for name in {"key", "revision_ids"}:
            values.pop(name, None)
        return values

    @api.model_create_multi
    def create(self, vals_list):
        self.sudo(False).check_access("create")
        with self.env.cr.savepoint():
            prepared = [self._prepare_identity(values) for values in vals_list]
            records = super().create(prepared)
            records._check_authority()
            return records

    def _prepare_identity(self, values):
        values = dict(values)
        if (SCOPE - {"solution_id"} | {"key", "revision_ids"}) & values.keys():
            raise ValidationError(
                _("Identity key, scope and history are server managed.")
            )
        solution = self._checked_relation(
            "project.agile.solution", values.get("solution_id")
        )
        solution.sudo(False).check_access("write")
        solution.project_id.sudo(False).check_access("write")
        self._check_active_solution(solution)
        lock_records(solution, serialize=True)
        lock_records(solution.project_id, serialize=True)
        # Authorized Project lock serializes first-use sequence creation even
        # across different lineages; standard sequences never reuse consumed keys.
        code = f"{self._name}.{solution.project_id.id}"
        sequence_model = self.env["ir.sequence"].sudo()
        sequence = sequence_model.search([("code", "=", code)], limit=1)
        if not sequence:
            sequence = sequence_model.create(
                {
                    "name": code,
                    "code": code,
                    "company_id": solution.company_id.id or False,
                    "prefix": self._key_prefix,
                    "padding": 0,
                    "implementation": "standard",
                }
            )
        values["key"] = sequence.next_by_id()
        return values

    def _check_active_solution(self, solution):
        if (
            not solution.active
            or not solution.project_id.active
            or not solution.project_id.agile_enabled
        ):
            raise ValidationError(_("Select an active Agile solution."))

    def _lock_identity(self):
        lock_records(self.solution_id, serialize=True)
        lock_records(self.project_id)
        lock_records(self, serialize=True)

    def write(self, values):
        self._check_authority()
        self._lock_identity()
        if (SCOPE | {"key", "revision_ids", "kind"}) & values.keys():
            raise ValidationError(
                _(
                    "Identity key, kind, scope and revision history "
                    "cannot be reassigned."
                )
            )
        return super().write(values)

    # Stable content identities cannot be deleted; archive is the supported path.
    def unlink(self):  # pylint: disable=method-required-super
        self._check_authority("unlink")
        raise ValidationError(  # pylint: disable=no-raise-unlink
            _("Retain stable content identities; archive instead of deleting.")
        )

    # Identity/revision creation is explicit, not a generic copy operation.
    def copy(self, default=None):  # pylint: disable=method-required-super
        raise ValidationError(
            _("Create a new identity explicitly; use New Revision for content changes.")
        )

    def _complete_revisions(self):
        self.ensure_one()
        revisions = self.with_context(active_test=False).revision_ids
        total = (
            self.env[self._revision_model]
            .sudo()
            .search_count([(self._identity_field, "=", self.id)])
        )
        if len(revisions) != total:
            raise AccessError(
                _("Required content history is unavailable under current access.")
            )
        return revisions.sorted("number")

    def action_new_revision(self):
        self.ensure_one()
        self._check_authority()
        self._lock_identity()
        self._check_active_solution(self.solution_id)
        revisions = self._complete_revisions()
        if not revisions:
            return {
                "type": "ir.actions.act_window",
                "res_model": self._revision_model,
                "view_mode": "form",
                "context": {
                    "default_" + self._identity_field: self.id,
                    "default_title": self.name,
                },
            }
        if revisions and not revisions[-1].sealed:
            revision = revisions[-1]
        else:
            values = (
                revisions[-1]._copy_content_values()
                if revisions
                else {"title": self.name}
            )
            values[self._identity_field] = self.id
            revision = self.env[self._revision_model].create(values)
        return {
            "type": "ir.actions.act_window",
            "res_model": revision._name,
            "res_id": revision.id,
            "view_mode": "form",
        }


class ContentRevision(models.AbstractModel):
    _name = "project.agile.solution.content.revision"
    _inherit = "project.agile.solution.access"
    _description = "Exact Solution Content Revision Mechanics"

    title = fields.Char(required=True)
    number = fields.Integer(required=True, readonly=True, copy=False)
    sealed = fields.Boolean(readonly=True, copy=False, default=False)
    sealed_at = fields.Datetime(readonly=True, copy=False)
    sealed_by_id = fields.Many2one(
        "res.users", readonly=True, copy=False, ondelete="restrict"
    )
    audience = fields.Selection(
        [("internal", "Internal Only"), ("customer", "Customer Projection")],
        required=True,
        default="internal",
    )

    @api.model
    def default_get(self, names):
        values = super().default_get(
            [name for name in names if name not in AUDIT | SCOPE | self._inverse_fields]
        )
        for name in AUDIT | SCOPE | self._inverse_fields:
            values.pop(name, None)
        return values

    @api.model_create_multi
    # _create_content delegates only after validating and locking the identity.
    def create(self, vals_list):  # pylint: disable=method-required-super
        self.sudo(False).check_access("create")
        records = self.browse()
        with self.env.cr.savepoint():
            for values in vals_list:
                records |= self._create_content(values)
        return records

    def _create_content(self, values):
        values = dict(values)
        if (AUDIT | SCOPE | self._inverse_fields) & values.keys():
            raise ValidationError(
                _("Content identity, seal and audit are server managed.")
            )
        identity = self._checked_relation(
            self._identity_model, values.get(self._identity_field)
        )
        identity._check_authority()
        identity._lock_identity()
        identity._check_active_solution(identity.solution_id)
        if not identity.active:
            raise ValidationError(
                _("Use an active content identity for new revisions.")
            )
        history = identity._complete_revisions()
        if history and not history[-1].sealed:
            raise ValidationError(_("Edit the existing working content revision."))
        predecessor = history[-1] if history else self.browse()
        values.update(
            number=predecessor.number + 1 if predecessor else 1,
            predecessor_id=predecessor.id or False,
        )
        self._check_input(values)
        record = super().create(values)
        record._validate_content()
        return record

    def _check_editable(self):
        self._check_authority()
        self[self._identity_field]._lock_identity()
        lock_records(self)
        if any(record.sealed for record in self):
            raise ValidationError(
                _("Referenced content is immutable; create a numbered successor.")
            )

    def write(self, values):
        self._check_editable()
        if (
            AUDIT | SCOPE | self._inverse_fields | {self._identity_field}
        ) & values.keys():
            raise ValidationError(
                _(
                    "Content identity, seal, history and inverse references "
                    "cannot be written."
                )
            )
        self._check_input(values)
        with self.env.cr.savepoint():
            result = super().write(values)
            self._validate_content()
            self._check_draft_memberships()
            return result

    def _check_draft_memberships(self):
        """No relational command may leave a draft referencing foreign/invalid
        content.
        """
        for revision in self:
            documents = revision.document_revision_ids.sudo(False)
            documents.check_access("read")
            total = (
                self.env["project.agile.solution.revision"]
                .sudo()
                .search_count([(self._document_field, "in", revision.ids)])
            )
            if total != len(documents):
                raise AccessError(
                    _("Required document context is unavailable under current access.")
                )
            documents._validate_content()

    # Numbered revisions are retained even when still editable.
    def unlink(self):  # pylint: disable=method-required-super
        self._check_editable()
        # No deleting numbered rows: future numbers and pointers must stay stable.
        raise ValidationError(  # pylint: disable=no-raise-unlink
            _("Retain revision history; remove draft membership instead.")
        )

    # Successor numbering must pass through the identity's action.
    def copy(self, default=None):  # pylint: disable=method-required-super
        raise ValidationError(_("Use the identity New Revision action, not Copy."))

    # Internal sealing has side effects, not the underlying write result API.
    def _seal(self):  # pylint: disable=missing-return
        """Private extension seam for already-authorized baseline/link/Sprint use."""
        self._check_authority()
        self[self._identity_field]._lock_identity()
        lock_records(self)
        self._validate_content()
        for record in self.filtered(lambda row: not row.sealed):
            super(ContentRevision, record.sudo()).write(
                {
                    "sealed": True,
                    "sealed_at": fields.Datetime.now(),
                    "sealed_by_id": self.env.user.id,
                }
            )

    def _check_input(self, values):
        return None

    def _validate_content(self):
        for record in self:
            if not (record.title or "").strip():
                raise ValidationError(_("Content requires a meaningful title."))
            record[self._identity_field].sudo(False).check_access("read")

    def _copy_content_values(self):
        self.ensure_one()
        self.sudo(False).check_access("read")
        return {"title": self.title, "audience": self.audience}

    def _snapshot_values(self):
        self.ensure_one()
        self.sudo(False).check_access("read")
        self._validate_content()
        identity = self[self._identity_field]
        return {
            "revision_id": self.id,
            "identity_id": identity.id,
            "key": identity.key,
            "number": self.number,
            **self._copy_content_values(),
        }

    def _check_snapshot_reference(self, payload):
        self.sudo(False).check_access("read")
        if not self.exists():
            raise AccessError(
                _("The exact content is unavailable under current access.")
            )
        self[self._identity_field].sudo(False).check_access("read")

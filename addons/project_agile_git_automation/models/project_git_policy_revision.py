"""Typed revisions: editable drafts, immutable approved records, explicit successors."""

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .policy_authority import (
    check_identity,
    check_task_authority,
    clean_context,
    exact_name,
    reject_keys,
    require_capability,
    stage_fingerprint,
)
from .policy_authority_profile import check_supported_profile

SELECTORS = {
    "target_branch",
    "allowed_source_stage_ids",
    "target_stage_id",
    "required_check_ids",
    "execution_user_id",
    "trigger",
    "effect",
}


def _check_stage_commands(values):
    """Link existing stages, never create/edit/delete native stages through policy."""
    if "allowed_source_stage_ids" not in values:
        return
    commands = values["allowed_source_stage_ids"]
    if not isinstance(commands, (list, tuple)):
        raise ValidationError(_("Source stages require finite relation commands."))
    for command in commands:
        if not isinstance(command, (list, tuple)) or len(command) != 3:
            raise ValidationError(_("Source stages require finite relation commands."))
        if command[0] not in (Command.LINK, Command.UNLINK, Command.CLEAR, Command.SET):
            raise ValidationError(
                _("Policy cannot create, edit or delete native stages.")
            )


class ProjectGitPolicyRevision(models.Model):
    _name = "project.git.policy.revision"
    _inherit = "project.git.policy.scope"
    _description = "Git Workflow Policy Revision"
    _check_company_auto = True
    _order = "rule_id, revision desc"
    _rec_name = "target_branch"

    rule_id = fields.Many2one(
        "project.git.policy.rule",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    repository_id = fields.Many2one(
        related="rule_id.repository_id", store=True, readonly=True
    )
    project_id = fields.Many2one(
        related="rule_id.project_id", store=True, readonly=True
    )
    company_id = fields.Many2one(
        related="rule_id.company_id", store=True, readonly=True
    )
    revision = fields.Integer(required=True, readonly=True, copy=False)
    owner_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict", copy=False
    )
    approver_id = fields.Many2one(
        "res.users", readonly=True, ondelete="restrict", copy=False
    )
    approved_at = fields.Datetime(readonly=True, copy=False)
    execution_user_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    trigger = fields.Selection(
        [("merged_pull_request", "Merged Pull Request")],
        required=True,
        default="merged_pull_request",
    )
    effect = fields.Selection(
        [("task_stage_transition", "Task Stage Transition")],
        required=True,
        default="task_stage_transition",
    )
    target_branch = fields.Char(required=True)
    allowed_source_stage_ids = fields.Many2many(
        "project.task.type", string="Allowed From Stages", required=True
    )
    target_stage_id = fields.Many2one(
        "project.task.type", required=True, ondelete="restrict"
    )
    required_check_ids = fields.One2many(
        "project.git.policy.required.check",
        "revision_id",
        string="Exact Required Checks",
    )

    _revision_unique = models.Constraint(
        "UNIQUE(rule_id, revision)", "Revision numbers must be unique within a rule."
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_capability(self.env)
        values_list = []
        numbers = {}
        for values in vals_list:
            reject_keys(values, SELECTORS | {"rule_id"})
            _check_stage_commands(values)
            rule = self.env["project.git.policy.rule"].browse(values.get("rule_id"))
            rule._check_control(owner=True)
            if rule.id not in numbers:
                previous = self.search(
                    [("rule_id", "=", rule.id)], order="revision desc", limit=1
                )
                numbers[rule.id] = previous.revision
            numbers[rule.id] += 1
            rule._revoke("revision_changed")
            values_list.append(
                {
                    **values,
                    "revision": numbers[rule.id],
                    "owner_id": rule.owner_id.id,
                    "approver_id": False,
                    "approved_at": False,
                    "trigger": values.get("trigger", "merged_pull_request"),
                    "effect": values.get("effect", "task_stage_transition"),
                }
            )
        return super(
            # Replacement strips caller defaults; merging would restore them.
            ProjectGitPolicyRevision,
            self.with_context(clean_context(self.env)),  # pylint: disable=context-overridden
        ).create(values_list)

    def _check_editable(self):
        self.check_access("write")
        self.rule_id._check_control(owner=True)
        if any(revision.approved_at for revision in self):
            raise ValidationError(
                _("Approved policy revisions are immutable; create a successor.")
            )
        if any(revision.owner_id != revision.rule_id.owner_id for revision in self):
            raise ValidationError(_("Ownership changes require a fresh revision."))

    @api.constrains(
        "target_branch",
        "allowed_source_stage_ids",
        "target_stage_id",
        "required_check_ids",
        "execution_user_id",
    )
    def _check_selectors(self):
        for revision in self:
            exact_name(revision.target_branch, "Target branch", branch=True)
            if not 1 <= len(revision.allowed_source_stage_ids) <= 20:
                raise ValidationError(
                    _("Policy requires 1 to 20 allowed source stages.")
                )
            if revision.target_stage_id in revision.allowed_source_stage_ids:
                raise ValidationError(
                    _("Target stage must be outside allowed source stages.")
                )
            if len(revision.required_check_ids) > 20:
                raise ValidationError(
                    _("At most 20 exact required check names are supported.")
                )
            stage_fingerprint(revision)
            check_identity(revision.execution_user_id, revision.repository_id)

    def write(self, values):
        self._check_editable()
        reject_keys(values, SELECTORS)
        _check_stage_commands(values)
        self.rule_id._revoke("revision_changed")
        return super().write(values)

    # Revisions are retained evidence; calling super would permit deletion.
    def unlink(self):  # pylint: disable=method-required-super
        # Rejection is the invariant, not an uninstall-time cleanup hook.
        raise ValidationError(  # pylint: disable=no-raise-unlink
            _("Policy revisions are retained; archive the rule instead.")
        )

    def action_new_revision(self):
        """Copy finite selectors only;
        never carry forward approval, epoch, or cutoff.
        """
        self.ensure_one()
        self.rule_id._check_control(owner=True)
        revision = self.create(
            {
                "rule_id": self.rule_id.id,
                "execution_user_id": self.execution_user_id.id,
                "target_branch": self.target_branch,
                "target_stage_id": self.target_stage_id.id,
                "allowed_source_stage_ids": [
                    Command.set(self.allowed_source_stage_ids.ids)
                ],
                "required_check_ids": [
                    Command.create({"name": check.name})
                    for check in self.required_check_ids
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": revision.id,
            "view_mode": "form",
            "context": {},
        }

    def _check_activation(self, acknowledgment):
        require_capability(self.env)
        self.check_access("write")
        self.rule_id._check_control()
        if self.approved_at:
            raise ValidationError(
                _("A used revision requires a fresh successor and approval.")
            )
        if self.owner_id == self.env.user or self.owner_id != self.rule_id.owner_id:
            raise AccessError(
                _(
                    "A different current capability holder "
                    "must approve the owner's revision."
                )
            )
        project = self.project_id
        if not project.git_policy_enabled:
            raise ValidationError(_("Explicit Project policy enablement is required."))
        if acknowledgment is not True:
            raise ValidationError(
                _("Explicit acknowledgment of native stage side effects is required.")
            )
        self._check_selectors()
        check_identity(self.owner_id, self.repository_id, manager=True)
        check_identity(self.env.user, self.repository_id, manager=True)
        check_supported_profile(
            self.repository_id, self.owner_id | self.env.user | self.execution_user_id
        )
        check_task_authority(self.owner_id, self.repository_id)
        check_task_authority(self.env.user, self.repository_id)
        check_task_authority(self.execution_user_id, self.repository_id)

    def action_activate(self, acknowledge_native_side_effects=False):
        """Approve exactly this revision and append an immutable server-timed epoch."""
        self.ensure_one()
        self._check_activation(acknowledge_native_side_effects)
        self.rule_id._revoke("replaced")
        timestamp = fields.Datetime.now()
        super(ProjectGitPolicyRevision, self.sudo()).write(
            {
                "approver_id": self.env.uid,
                "approved_at": timestamp,
            }
        )
        activation = self.env["project.git.policy.activation"]._create_approved(
            self, timestamp
        )
        self.rule_id._set_activation(activation)
        return {"activation_id": activation.id}

    def action_activate_from_form(self):
        """Open an explicit acknowledgment wizard, not a context-controlled approval."""
        self.ensure_one()
        require_capability(self.env)
        self.check_access("read")
        self.rule_id._check_control()
        wizard = self.env["project.git.policy.approval.wizard"].create(
            {"revision_id": self.id}
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
            "context": {},
        }

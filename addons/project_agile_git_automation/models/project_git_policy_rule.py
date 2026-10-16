"""Stable scoped rule identities; drafts and approval epochs are separate records."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .policy_authority import (
    check_identity,
    check_scope,
    clean_context,
    reject_keys,
    require_capability,
)


class ProjectGitPolicyRule(models.Model):
    _name = "project.git.policy.rule"
    _inherit = "project.git.policy.scope"
    _description = "Git Workflow Policy Rule"
    _check_company_auto = True
    _order = "project_id, id"

    name = fields.Char(required=True)
    repository_id = fields.Many2one(
        "project.git.repository",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    project_id = fields.Many2one(
        "project.project", required=True, readonly=True, ondelete="restrict", index=True
    )
    company_id = fields.Many2one(
        "res.company", required=True, readonly=True, ondelete="restrict", index=True
    )
    owner_id = fields.Many2one(
        "res.users", required=True, readonly=True, ondelete="restrict"
    )
    active = fields.Boolean(default=True)
    authority_epoch = fields.Integer(default=0, readonly=True, copy=False)
    activation_id = fields.Many2one(
        "project.git.policy.activation", readonly=True, ondelete="restrict", copy=False
    )
    active_revision_id = fields.Many2one(
        related="activation_id.revision_id", readonly=True
    )
    revision_ids = fields.One2many(
        "project.git.policy.revision", "rule_id", readonly=True
    )
    last_effect_id = fields.Many2one(
        "project.git.policy.effect",
        readonly=True,
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help=(
            "Private effect publication marker creating an ORM shared-row conflict "
            "with competing rule authority/revocation changes. Not authorization, "
            "a lease counter or a recovery/navigation feature."
        ),
    )

    def _record_effect(self, effect):
        """Publish effect for an ORM conflict with rule authority/revocation changes."""
        self.ensure_one()
        if effect.revision_id.rule_id != self:
            raise ValidationError(_("Policy effect must retain its rule."))
        return super(ProjectGitPolicyRule, self.sudo()).write(
            {"last_effect_id": effect.id}
        )

    policy_status = fields.Selection(
        [("disabled", "Disabled"), ("dry_run", "Dry Run"), ("active", "Active")],
        compute="_compute_policy_status",
        compute_sudo=False,
    )

    @api.depends(
        "active",
        "activation_id",
        "activation_id.mode",
        "activation_id.revocation_ids",
        "project_id.git_policy_enabled",
        "project_id.git_policy_mode",
    )
    def _compute_policy_status(self):
        """Display persisted control state, not a certification of current
        Task access.
        """
        for rule in self:
            activation = rule.activation_id
            enabled = (
                rule.active
                and rule.project_id.git_policy_enabled
                and activation
                and not activation.revocation_ids
            )
            rule.policy_status = (
                "active"
                if enabled
                and activation.mode == "apply"
                and rule.project_id.git_policy_mode == "apply"
                else "dry_run"
                if enabled
                and activation.mode == "dry_run"
                and rule.project_id.git_policy_mode == "dry_run"
                else "disabled"
            )

    @api.model_create_multi
    def create(self, vals_list):
        require_capability(self.env)
        values_list = []
        for values in vals_list:
            reject_keys(values, {"name", "repository_id"})
            repository = self.env["project.git.repository"].browse(
                values.get("repository_id")
            )
            check_scope(repository)
            values_list.append(
                {
                    **values,
                    "project_id": repository.project_id.id,
                    "company_id": repository.company_id.id,
                    "owner_id": self.env.uid,
                    "active": True,
                    "authority_epoch": 0,
                    "activation_id": False,
                }
            )
        return super(
            # Caller defaults must be removed, not merged back into this create.
            ProjectGitPolicyRule,
            self.with_context(clean_context(self.env)),  # pylint: disable=context-overridden
        ).create(values_list)

    def _check_control(self, owner=False, emergency=False):
        require_capability(self.env, emergency=emergency)
        self.check_access("read" if emergency else "write")
        # Read authority remains necessary for emergency shutdown even when an
        # archived/moved repository is no longer eligible for new activation.
        self.project_id.check_access("read" if emergency else "write")
        self.repository_id.check_access("read" if emergency else "write")
        if not emergency:
            for rule in self:
                check_scope(rule.repository_id, rule.project_id, rule.company_id)
                if not rule.active:
                    raise ValidationError(
                        _("Archived policy identities cannot be reused.")
                    )
                if owner and rule.owner_id != self.env.user:
                    raise AccessError(
                        _("Only the current policy owner can edit its drafts.")
                    )

    # Terminal update is side-effect-only, not an inherited write return API.
    def _revoke(self, reason):  # pylint: disable=missing-return
        """Private terminal epoch update; callers authorize or revoke-only
        native hooks.
        """
        for rule in self:
            if rule.activation_id:
                rule.activation_id._revoke(reason)
            super(ProjectGitPolicyRule, rule.sudo()).write(
                {
                    "authority_epoch": rule.authority_epoch + 1,
                    "activation_id": False,
                }
            )

    # Private control update intentionally returns no native write result.
    def _set_activation(self, activation):  # pylint: disable=missing-return
        self.ensure_one()
        super(ProjectGitPolicyRule, self.sudo()).write(
            {"activation_id": activation.id if activation else False}
        )

    def write(self, values):
        self._check_control(owner=True)
        reject_keys(values, {"name", "active"})
        if values.get("active"):
            raise ValidationError(
                _("Policy identities cannot be recycled through unarchive.")
            )
        self._revoke("rule_changed" if values.get("active", True) else "archived")
        return super().write(values)

    # Deletion deliberately archives; super would erase retained history.
    def unlink(self):  # pylint: disable=method-required-super
        """Deletion requests archive identities.

        Retain revision/activation tombstones.
        """
        self._check_control(owner=True)
        self.write({"active": False})
        return True

    def action_disable(self):
        """Emergency revoke, including visible System Administrators; never enables."""
        self._check_control(emergency=True)
        self._revoke("disabled")
        return True

    def action_preview(self):
        """Preview the fixed readable repository, never caller-selected Tasks
        or effects.
        """
        self.ensure_one()
        require_capability(self.env)
        # Strip caller defaults before resolving the fixed preview target.
        # pylint: disable-next=context-overridden
        rule = self.with_context(clean_context(self.env))
        rule.check_access("read")
        return rule.repository_id.action_dry_run_git_policy()

    def action_transfer_owner(self, new_owner_id):
        self.ensure_one()
        self._check_control(owner=True)
        if type(new_owner_id) is not int or new_owner_id <= 0:
            raise ValidationError(_("An explicit policy owner is required."))
        owner = self.env["res.users"].browse(new_owner_id).exists()
        check_identity(owner, self.repository_id, manager=True)
        self._revoke("owner_changed")
        super(ProjectGitPolicyRule, self.sudo()).write({"owner_id": owner.id})
        return True

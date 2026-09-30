"""Explicit opt-in controls; raw RPC fields and context cannot enable policy."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .policy_authority import MODES, clean_context, lock_records, require_capability


CONTROLS = {"git_policy_enabled", "git_policy_mode", "git_policy_authority_epoch"}
PROJECT_AUTHORITY_FIELDS = {
    "active", "company_id", "agile_enabled", "privacy_visibility", "message_partner_ids", "user_id",
}


class ProjectProject(models.Model):
    _inherit = "project.project"

    git_policy_enabled = fields.Boolean(default=False, readonly=True, copy=False)
    git_policy_mode = fields.Selection(MODES, required=True, default="dry_run", readonly=True, copy=False)
    git_policy_authority_epoch = fields.Integer(default=0, readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        values_list = []
        for values in vals_list:
            if CONTROLS.intersection(values):
                raise ValidationError(_("Project policy controls require explicit authorized actions."))
            values_list.append({**values, "git_policy_enabled": False, "git_policy_mode": "dry_run", "git_policy_authority_epoch": 0})
        context = {key: value for key, value in self.env.context.items() if not key.startswith("default_git_policy_")}
        return super(ProjectProject, self.with_context(context)).create(values_list)

    def write(self, values):
        if CONTROLS.intersection(values):
            raise ValidationError(_("Project policy controls require explicit authorized actions."))
        if PROJECT_AUTHORITY_FIELDS.intersection(values):
            lock_records(self)
        result = super().write(values)
        if PROJECT_AUTHORITY_FIELDS.intersection(values):
            self._git_policy_invalidate("project_changed")
        return result

    def _git_policy_invalidate(self, reason):
        lock_records(self)
        self.env["project.git.policy.activation"]._revoke_matching([("project_id", "in", self.ids)], reason)
        for project in self:
            super(ProjectProject, project.sudo()).write({"git_policy_authority_epoch": project.git_policy_authority_epoch + 1})

    def action_enable_git_policy(self, mode="dry_run"):
        self.ensure_one()
        require_capability(self.env)
        self.check_access("write")
        lock_records(self)
        self.check_access("write")
        if mode not in dict(MODES):
            raise ValidationError(_("Only finite dry-run/apply modes are supported."))
        if not self.company_id or self.company_id not in self.env.companies:
            raise AccessError(_("Policy requires a currently visible company-scoped project."))
        if not self.active or not self.agile_enabled:
            raise ValidationError(_("Policy requires an active Agile project."))
        self._git_policy_invalidate("project_changed")
        super(ProjectProject, self.sudo()).write({"git_policy_enabled": True, "git_policy_mode": mode})
        return True

    def action_disable_git_policy(self):
        require_capability(self.env, emergency=True)
        self.check_access("read")
        lock_records(self)
        require_capability(self.env, emergency=True)
        self.check_access("read")
        self._git_policy_invalidate("disabled")
        super(ProjectProject, self.sudo()).write({"git_policy_enabled": False, "git_policy_mode": "dry_run"})
        return True

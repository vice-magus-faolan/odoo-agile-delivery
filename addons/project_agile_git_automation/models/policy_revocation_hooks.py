"""Revoke-only native hooks: restoration never resurrects a used approval epoch."""

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL

from .policy_authority import STAGE_SETTINGS, lock_records


def _policy_ready(env):
    """Internal install/uninstall schema check, never a caller context bypass."""
    if "project.git.policy.activation" not in env.registry:
        return False
    env.cr.execute(SQL("SELECT to_regclass('project_git_policy_activation')"))
    return bool(env.cr.fetchone()[0])


def _revoke(env, domain, reason):
    """Fixed internal revoke boundary, never grants permission or returns hidden IDs.

    The native create/write/unlink has already authorized and succeeded. On load
    and uninstall the policy table may not yet exist; this is a schema check, not
    a caller-controlled bypass. Direct DB administration remains the trust root.
    """
    if _policy_ready(env):
        env["project.git.policy.activation"]._revoke_matching(domain, reason)


class ProjectGitRepository(models.Model):
    _inherit = "project.git.repository"

    def write(self, values):
        self.check_access("write")
        rules = self.env["project.git.policy.rule"].sudo().with_context(active_test=False).search([
            ("repository_id", "in", self.ids),
        ])
        if rules and {"provider", "provider_repository_id"}.intersection(values):
            raise ValidationError(_("Repositories with policy history cannot change provider identity; archive instead."))
        relevant = {"active", "project_id", "canonical_url", "retention_policy", "webhook_secret"}.intersection(values)
        if relevant:
            lock_records(self.project_id)
            lock_records(self)
        result = super().write(values)
        if relevant:
            _revoke(self.env, [("repository_id", "in", self.ids)], "repository_changed")
        return result


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    def write(self, values):
        result = super().write(values)
        if set(STAGE_SETTINGS).intersection(values):
            _revoke(self.env, ["|", ("revision_id.target_stage_id", "in", self.ids),
                               ("revision_id.allowed_source_stage_ids", "in", self.ids)], "stage_changed")
        return result

    def unlink(self):
        self.check_access("unlink")
        if self.env["project.git.policy.revision"].sudo().search_count([
            ("allowed_source_stage_ids", "in", self.ids),
        ]):
            raise ValidationError(_("Policy stage history must be preserved; archive or unlink it from the Project instead."))
        return super().unlink()


class ProjectTaskStagePersonal(models.Model):
    """Native table alias can change Task assignees without Task.write."""

    _inherit = "project.task.stage.personal"

    def _git_policy_project_ids(self):
        return self.sudo().task_id.project_id.ids

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _revoke(self.env, [("project_id", "in", records._git_policy_project_ids())], "authority_changed")
        return records

    def write(self, values):
        self.check_access("write")
        relevant = {"task_id", "user_id"}.intersection(values)
        before = self._git_policy_project_ids() if relevant else []
        result = super().write(values)
        if relevant:
            projects = sorted(set(before) | set(self._git_policy_project_ids()))
            _revoke(self.env, [("project_id", "in", projects)], "authority_changed")
        return result

    def unlink(self):
        self.check_access("unlink")
        projects = self._git_policy_project_ids()
        result = super().unlink()
        _revoke(self.env, [("project_id", "in", projects)], "authority_changed")
        return result


class MailFollowers(models.Model):
    _inherit = "mail.followers"

    def _git_policy_project_ids(self):
        """Fixed document mapping for revoke-only hooks after follower authorization.

        Native unsubscribe deletes followers directly, without Project.write.
        Task IDs are read only to find their Project; no hidden IDs are exposed
        and no Task/follower mutation is added by this hook.
        """
        projects = self.filtered(lambda follower: follower.res_model == "project.project")
        tasks = self.filtered(lambda follower: follower.res_model == "project.task")
        task_projects = self.env["project.task"].sudo().browse(tasks.mapped("res_id")).exists().project_id
        return sorted(set(projects.mapped("res_id")) | set(task_projects.ids))

    def write(self, values):
        relevant = {"res_model", "res_id", "partner_id"}.intersection(values)
        self.check_access("write")
        project_ids = self._git_policy_project_ids() if relevant else []
        result = super().write(values)
        if relevant:
            project_ids = sorted(set(project_ids) | set(self._git_policy_project_ids()))
            _revoke(self.env, [("project_id", "in", project_ids)], "authority_changed")
        return result

    def unlink(self):
        self.check_access("unlink")
        project_ids = self._git_policy_project_ids()
        result = super().unlink()
        if project_ids:
            _revoke(self.env, [("project_id", "in", project_ids)], "authority_changed")
        return result


class ResUsers(models.Model):
    _inherit = "res.users"

    def write(self, values):
        result = super().write(values)
        if {"active", "group_ids", "all_group_ids", "company_ids", "company_id", "share", "role", "partner_id"}.intersection(values):
            _revoke(self.env, ["|", "|", ("owner_id", "in", self.ids),
                               ("approver_id", "in", self.ids), ("execution_user_id", "in", self.ids)], "identity_changed")
        return result


class ResGroups(models.Model):
    _inherit = "res.groups"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _revoke(self.env, [], "security_changed")
        return records

    def write(self, values):
        result = super().write(values)
        if {"implied_ids", "user_ids", "all_user_ids"}.intersection(values):
            _revoke(self.env, [], "security_changed")
        return result

    def unlink(self):
        result = super().unlink()
        _revoke(self.env, [], "security_changed")
        return result


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _revoke(self.env, [], "identity_changed")
        return records

    def write(self, values):
        result = super().write(values)
        if {"user_ids", "active"}.intersection(values):
            # M2M inverse edits do not necessarily invoke res.users.write.
            _revoke(self.env, [], "identity_changed")
        return result


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, values):
        result = super().write(values)
        if "company_id" in values:
            # Project.company_id depends on partner_id.company_id. Conservatively
            # cover computed propagation without pretending it invokes Project.write.
            _revoke(self.env, [], "authority_changed")
        return result

    def unlink(self):
        result = super().unlink()
        _revoke(self.env, [], "authority_changed")
        return result


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def write(self, values):
        result = super().write(values)
        if "company_id" in values:
            # The other native computed Project company dependency is analytic.
            _revoke(self.env, [], "authority_changed")
        return result

    def unlink(self):
        result = super().unlink()
        _revoke(self.env, [], "authority_changed")
        return result


class IrModelData(models.Model):
    _inherit = "ir.model.data"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _revoke(self.env, [], "security_changed")
        return records

    def write(self, values):
        result = super().write(values)
        _revoke(self.env, [], "security_changed")
        return result

    def unlink(self):
        result = super().unlink()
        _revoke(self.env, [], "security_changed")
        return result


class IrRule(models.Model):
    _inherit = "ir.rule"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _revoke(self.env, [], "security_changed")
        return records

    def write(self, values):
        result = super().write(values)
        _revoke(self.env, [], "security_changed")
        return result

    def unlink(self):
        result = super().unlink()
        _revoke(self.env, [], "security_changed")
        return result


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _revoke(self.env, [], "security_changed")
        return records

    def write(self, values):
        result = super().write(values)
        _revoke(self.env, [], "security_changed")
        return result

    def unlink(self):
        result = super().unlink()
        _revoke(self.env, [], "security_changed")
        return result

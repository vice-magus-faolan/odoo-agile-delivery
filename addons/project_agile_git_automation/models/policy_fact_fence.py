"""Optional observation fencing, never policy evaluation or workflow mutation.

A repository evidence counter supplies an MVCC write conflict as well as a mutex.
Row locks alone cannot refresh Odoo's repeatable-read snapshot after a waiter wakes.
Every ORM provenance input serializes with apply; rolled-back native operations
also roll back the counter. Core facts remain independently installable.
"""
from odoo import api, fields, models
from odoo.tools import SQL

from .policy_authority import lock_records
from .policy_revocation_hooks import _policy_ready


class ProjectGitRepository(models.Model):
    _inherit = "project.git.repository"

    git_policy_evidence_version = fields.Integer(default=0, readonly=True, copy=False, groups="base.group_system")


def fence_inputs(records, vals_list=()):
    """Internal fixed repository mapping; native ACLs/validation remain authoritative."""
    if not _policy_ready(records.env):
        return
    ids = records.sudo().repository_id.ids
    ids += [v["repository_id"] for v in vals_list if type(v.get("repository_id")) is int]
    repositories = records.env["project.git.repository"].sudo().browse(sorted(set(ids))).exists()
    lock_records(repositories.project_id)
    lock_records(repositories)
    if repositories:
        records.env.cr.execute(SQL(
            "UPDATE project_git_repository SET git_policy_evidence_version = git_policy_evidence_version + 1 WHERE id IN %s",
            tuple(repositories.ids),
        ))
        repositories.invalidate_recordset(["git_policy_evidence_version"])


class PolicyEvidenceFence(models.AbstractModel):
    _name = "project.git.policy.evidence.fence"
    _description = "Private Optional Provenance Input Fence"

    @api.model_create_multi
    def create(self, vals_list):
        self.check_access("create")
        fence_inputs(self, vals_list)
        return super().create(vals_list)

    def write(self, values):
        self.check_access("write")
        fence_inputs(self, [values])
        return super().write(values)

    def unlink(self):
        self.check_access("unlink")
        fence_inputs(self)
        return super().unlink()


class ProjectGitPullRequest(models.Model):
    _name = "project.git.pull.request"
    _inherit = ["project.git.pull.request", "project.git.policy.evidence.fence"]


class ProjectGitCheck(models.Model):
    _name = "project.git.check"
    _inherit = ["project.git.check", "project.git.policy.evidence.fence"]


class ProjectGitDelivery(models.Model):
    _name = "project.git.delivery"
    _inherit = ["project.git.delivery", "project.git.policy.evidence.fence"]


class ProjectGitAssociationAudit(models.Model):
    _name = "project.git.association.audit"
    _inherit = ["project.git.association.audit", "project.git.policy.evidence.fence"]


class ProjectGitTaskAssociation(models.Model):
    _name = "project.git.task.association"
    _inherit = ["project.git.task.association", "project.git.policy.evidence.fence"]

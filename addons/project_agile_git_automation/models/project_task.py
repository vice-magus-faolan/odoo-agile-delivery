"""Observe bounded authority-input mutations, never initiate policy Task writes."""

from odoo import api, models

from .policy_authority import lock_records
from .policy_authority_profile import TASK_AUTHORITY_FIELDS, TASK_SCOPE_FIELDS
from .policy_revocation_hooks import _policy_ready, _revoke


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _git_policy_lock_scopes(self, project_ids):
        """Fence controls before native Task row mutation; never authorize a write."""
        projects = self.env["project.project"].sudo().browse(sorted(set(project_ids))).exists()
        lock_records(projects)

    def _git_policy_requested_scopes(self, values):
        """Fixed scope-only hints for lock coverage, not provider/caller authority.

        The enclosing super still performs normal record/company validation.
        Nested child commands can touch several scopes; fence all existing policy
        Projects first in that uncommon path rather than invert child lock order.
        """
        if "child_ids" in values:
            if not _policy_ready(self.env):
                return []
            return self.env["project.git.policy.activation"].sudo().search([]).project_id.ids
        project_id = values.get("project_id", self.env.context.get("default_project_id"))
        projects = [project_id] if type(project_id) is int and project_id > 0 else []
        parent_id = values.get("parent_id", self.env.context.get("default_parent_id"))
        if type(parent_id) is int and parent_id > 0:
            projects += self.sudo().browse(parent_id).exists().project_id.ids
        return projects

    def _git_policy_affected_projects(self, descendants=False):
        """Private scope-only read after native authorization, never return to RPC.

        Native parent edits can recompute descendant project/company without a
        descendant write override. Capture their old AND recomputed new scopes.
        No name, key, user or other hidden business data is read or exposed.
        """
        tasks = self.sudo().with_context(active_test=False)
        if descendants and tasks:
            tasks = tasks.search([("id", "child_of", tasks.ids)])
        return tasks.project_id.ids

    @api.model_create_multi
    def create(self, vals_list):
        self.check_access("create")
        requested = [project for values in vals_list for project in self._git_policy_requested_scopes(values)]
        self._git_policy_lock_scopes(requested)
        records = super().create(vals_list)
        _revoke(self.env, [("project_id", "in", sorted(set(records._git_policy_affected_projects())))], "authority_changed")
        return records

    def write(self, values):
        self.check_access("write")
        relevant = (TASK_AUTHORITY_FIELDS | TASK_SCOPE_FIELDS).intersection(values)
        descendants = bool(TASK_SCOPE_FIELDS.intersection(values))
        before = self._git_policy_affected_projects(descendants) if relevant else []
        if relevant:
            requested = self._git_policy_requested_scopes(values) + self.sudo().parent_id.project_id.ids
            self._git_policy_lock_scopes(before + requested)
        result = super().write(values)
        if relevant:
            after = self._git_policy_affected_projects(descendants)
            _revoke(self.env, [("project_id", "in", sorted(set(before) | set(after)))], "authority_changed")
        return result

    def unlink(self):
        self.check_access("unlink")
        before = self._git_policy_affected_projects(descendants=True)
        self._git_policy_lock_scopes(before)
        result = super().unlink()
        _revoke(self.env, [("project_id", "in", sorted(set(before)))], "authority_changed")
        return result

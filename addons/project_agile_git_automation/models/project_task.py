"""Observe bounded authority-input mutations, never initiate policy Task writes."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL

from .policy_authority import lock_records
from .policy_authority_profile import TASK_AUTHORITY_FIELDS, TASK_SCOPE_FIELDS
from .policy_revocation_hooks import _policy_ready, _revoke


class ProjectTask(models.Model):
    _inherit = "project.task"

    git_policy_transition_version = fields.Integer(default=0, readonly=True, copy=False)

    def _git_policy_advance_transition(self):
        """Increment only the private token, not native business/tracking metadata."""
        if not self:
            return
        self.flush_recordset(["git_policy_transition_version"])
        self.env.cr.execute(SQL(
            "UPDATE project_task SET git_policy_transition_version = git_policy_transition_version + 1 WHERE id IN %s",
            tuple(self.ids),
        ))
        self.invalidate_recordset(["git_policy_transition_version"])

    @api.depends("stage_id", "depend_on_ids.state")
    def _compute_state(self):
        """Observe native dependency transitions, including propagation and reversal.

        Odoo 19 fields.Field.compute_value removes pending recomputation before
        invoking this method, so reading the old state here is supported (the
        native implementation also reads it). Do not flush all fields or lock
        through lock_records: that could recursively flush the current compute.
        The fixed row lock and counter-only update settle with the native compute
        in its transaction, including compute_sudo for inaccessible dependents.
        No native state, actor, timestamp or Scrum history is written by this hook.
        New/onchange records have no durable policy attempt and are excluded.
        """
        persisted = self.filtered("id")
        if persisted:
            self.env.cr.execute(SQL(
                "SELECT id FROM project_task WHERE id IN %s ORDER BY id FOR UPDATE",
                tuple(persisted.ids),
            ))
        before = {task.id: task.state for task in persisted}
        super()._compute_state()
        changed = persisted.filtered(lambda task: task.state != before[task.id])
        changed._git_policy_advance_transition()

    def _git_policy_fence_tasks(self, values):
        """Cover direct mutations and parent-propagated native scope recomputation."""
        inputs = {"stage_id", "state", "project_id", "company_id", "active", "parent_id", "child_ids"}
        if not inputs.intersection(values):
            return self.browse()
        tasks = self.sudo().with_context(active_test=False)
        if TASK_SCOPE_FIELDS.intersection(values):
            tasks = tasks.search([("id", "child_of", self.ids)])
        self._git_policy_lock_scopes(tasks.project_id.ids + self._git_policy_requested_scopes(values))
        lock_records(tasks)
        return tasks

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
        if any("git_policy_transition_version" in values for values in vals_list):
            raise ValidationError(_("Task transition fences are server-owned."))
        context = {k: v for k, v in self.env.context.items() if k != "default_git_policy_transition_version"}
        requested = [project for values in vals_list for project in self._git_policy_requested_scopes(values)]
        self._git_policy_lock_scopes(requested)
        records = super(ProjectTask, self.with_context(context)).create(vals_list)
        _revoke(self.env, [("project_id", "in", sorted(set(records._git_policy_affected_projects())))], "authority_changed")
        return records

    def write(self, values):
        self.check_access("write")
        if "git_policy_transition_version" in values:
            raise ValidationError(_("Task transition fences are server-owned."))
        fenced = self._git_policy_fence_tasks(values)
        relevant = (TASK_AUTHORITY_FIELDS | TASK_SCOPE_FIELDS).intersection(values)
        descendants = bool(TASK_SCOPE_FIELDS.intersection(values))
        before = self._git_policy_affected_projects(descendants) if relevant else []
        if relevant:
            requested = self._git_policy_requested_scopes(values) + self.sudo().parent_id.project_id.ids
            self._git_policy_lock_scopes(before + requested)
        result = super().write(values)
        # Native authorization/constraints succeed first. A counter-only SQL update
        # batches descendant compute fences and preserves native business write_uid,
        # tracking and timestamp semantics (a second ORM write would alter those).
        fenced._git_policy_advance_transition()
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

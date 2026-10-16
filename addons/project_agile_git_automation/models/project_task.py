"""Observe bounded authority-input mutations, never initiate policy Task writes."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .policy_authority_profile import TASK_AUTHORITY_FIELDS, TASK_SCOPE_FIELDS
from .policy_revocation_hooks import _revoke


class ProjectTask(models.Model):
    _inherit = "project.task"

    git_policy_transition_version = fields.Integer(
        compute="_compute_state", store=True, default=0, readonly=True, copy=False
    )

    def _git_policy_advance_transition(self):
        """Persist direct-input transitions through the remaining native write chain."""
        for task in self:
            super(ProjectTask, task).write(
                {
                    "git_policy_transition_version": task.git_policy_transition_version
                    + 1
                }
            )

        return True

    @api.depends("stage_id", "depend_on_ids.state")
    # Native compute and observer have side effects, not a return-value contract.
    def _compute_state(self):  # pylint: disable=missing-return
        """Keep the token with the native state compute, without a second state write.

        Both stored fields share this compute. Native field protection therefore
        persists the private token without reentering Task.write or changing the
        dependent Task actor, timestamps, tracking or Scrum completion history.
        Reading old values is supported by Field.compute_value, as for native state.
        Unchanged and unsaved dependency recomputes do not advance durable tokens.
        """
        before = {
            task.id: (task.state, task.git_policy_transition_version)
            for task in self
            if task.id
        }
        super()._compute_state()
        for task in self:
            old_state, version = before.get(task.id, (task.state, 0))
            task.git_policy_transition_version = version + bool(
                task.id and task.state != old_state
            )

    def _git_policy_fence_tasks(self, values):
        """Cover direct mutations and parent-propagated native scope recomputation."""
        inputs = {
            "stage_id",
            "state",
            "project_id",
            "company_id",
            "active",
            "parent_id",
            "child_ids",
        }
        if not inputs.intersection(values):
            return self.browse()
        tasks = self.sudo().with_context(active_test=False)
        if TASK_SCOPE_FIELDS.intersection(values):
            tasks = tasks.search([("id", "child_of", self.ids)])
        return tasks

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
        context = {
            k: v
            for k, v in self.env.context.items()
            if k != "default_git_policy_transition_version"
        }
        # Replacement removes the caller's transition-version default.
        # pylint: disable-next=context-overridden
        records = super(ProjectTask, self.with_context(context)).create(vals_list)
        _revoke(
            self.env,
            [
                (
                    "project_id",
                    "in",
                    sorted(set(records._git_policy_affected_projects())),
                )
            ],
            "authority_changed",
        )
        return records

    def write(self, values):
        self.check_access("write")
        if "git_policy_transition_version" in values:
            raise ValidationError(_("Task transition fences are server-owned."))
        fenced = self._git_policy_fence_tasks(values)
        relevant = (TASK_AUTHORITY_FIELDS | TASK_SCOPE_FIELDS).intersection(values)
        descendants = bool(TASK_SCOPE_FIELDS.intersection(values))
        before = self._git_policy_affected_projects(descendants) if relevant else []
        result = super().write(values)
        # Native authorization/constraints succeed first. Direct-input bookkeeping
        # follows the same actor; dependency-only computes use protected fields above.
        fenced._git_policy_advance_transition()
        if relevant:
            after = self._git_policy_affected_projects(descendants)
            _revoke(
                self.env,
                [("project_id", "in", sorted(set(before) | set(after)))],
                "authority_changed",
            )
        return result

    def unlink(self):
        self.check_access("unlink")
        before = self._git_policy_affected_projects(descendants=True)
        result = super().unlink()
        _revoke(
            self.env, [("project_id", "in", sorted(set(before)))], "authority_changed"
        )
        return result

"""Read-only standard-view navigation from Agile Projects and Tasks to Git facts."""

from odoo import api, fields, models

_TASK_FACT_SPECS = {
    "branch": (
        "git_branch_count",
        "project.git.branch",
        "provider_branch_id",
        "project_agile_git.action_project_git_branch",
    ),
    "commit": (
        "git_commit_count",
        "project.git.commit",
        "sha",
        "project_agile_git.action_project_git_commit",
    ),
    "pull_request": (
        "git_pull_request_count",
        "project.git.pull.request",
        "provider_request_id",
        "project_agile_git.action_project_git_pull_request",
    ),
    "check": (
        "git_check_count",
        "project.git.check",
        "provider_check_id",
        "project_agile_git.action_project_git_check",
    ),
}


class ProjectProject(models.Model):
    """Expose only repositories already visible through the current user's ORM rules."""

    _inherit = "project.project"

    git_repository_ids = fields.One2many(
        "project.git.repository", "project_id", readonly=True
    )
    git_repository_count = fields.Integer(compute="_compute_git_repository_count")

    @api.depends("git_repository_ids")
    def _compute_git_repository_count(self):
        """Count repositories with one access-checked grouped query."""

        for project in self:
            project.git_repository_count = 0
        rows = self.env["project.git.repository"]._read_group(
            [("project_id", "in", self.ids)], ["project_id"], ["__count"]
        )
        for project, count in rows:
            project.git_repository_count = count

    def action_open_git_repositories(self):
        """Open the current project repositories through the standard list/form
        action.
        """

        self.ensure_one()
        self.check_access("read")
        action = self.env["ir.actions.actions"]._for_xml_id(
            "project_agile_git.action_project_git_repository"
        )
        action["domain"] = [("project_id", "=", self.id)]
        action["context"] = {"default_project_id": self.id}
        return action


class ProjectTask(models.Model):
    """Navigate immutable association facts without trusting client-provided
    fact IDs.
    """

    _inherit = "project.task"

    git_association_ids = fields.One2many(
        "project.git.task.association", "task_id", readonly=True
    )
    git_branch_count = fields.Integer(compute="_compute_git_fact_counts")
    git_commit_count = fields.Integer(compute="_compute_git_fact_counts")
    git_pull_request_count = fields.Integer(compute="_compute_git_fact_counts")
    git_check_count = fields.Integer(compute="_compute_git_fact_counts")

    @api.depends("git_association_ids", "git_association_ids.source_type")
    def _compute_git_fact_counts(self):
        """Count visible associations in one grouped query for all rendered tasks."""

        for task in self:
            for (
                field_name,
                _model_name,
                _provider_field,
                _action_xml_id,
            ) in _TASK_FACT_SPECS.values():
                task[field_name] = 0
        rows = self.env["project.git.task.association"]._read_group(
            [("task_id", "in", self.ids)], ["task_id", "source_type"], ["__count"]
        )
        for task, source_type, count in rows:
            task[_TASK_FACT_SPECS[source_type][0]] = count

    def _action_open_task_git_facts(self, source_type):
        """Resolve fact IDs server-side from visible associations before opening
        a list.
        """

        self.ensure_one()
        self.check_access("read")
        _count_field, _model_name, provider_field, action_xml_id = _TASK_FACT_SPECS[
            source_type
        ]
        associations = self.env["project.git.task.association"].search_fetch(
            [("task_id", "=", self.id), ("source_type", "=", source_type)],
            ["repository_id", "source_provider_id"],
        )
        association_pairs = sorted(
            {
                (association.repository_id.id, association.source_provider_id)
                for association in associations
            }
        )
        domain = ["|"] * (len(association_pairs) - 1)
        for repository_id, source_provider_id in association_pairs:
            domain.extend(
                [
                    "&",
                    ("repository_id", "=", repository_id),
                    (provider_field, "=", source_provider_id),
                ]
            )
        action = self.env["ir.actions.actions"]._for_xml_id(action_xml_id)
        action["domain"] = domain or [("id", "=", False)]
        return action

    def action_open_git_branches(self):
        return self._action_open_task_git_facts("branch")

    def action_open_git_commits(self):
        return self._action_open_task_git_facts("commit")

    def action_open_git_pull_requests(self):
        return self._action_open_task_git_facts("pull_request")

    def action_open_git_checks(self):
        return self._action_open_task_git_facts("check")

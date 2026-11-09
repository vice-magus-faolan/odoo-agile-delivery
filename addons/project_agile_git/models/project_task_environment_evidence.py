"""Caller-scoped historical merge evidence, independent of manual task statuses."""

from collections import defaultdict

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain

_EVIDENCE_FIELDS = (
    "git_merge_environment_ids",
    "git_environment_merge_count",
    "git_environment_evidence",
    "git_uat_without_production_id",
)


class ProjectTask(models.Model):
    # Historical merge evidence is separate from Git fact navigation.
    # pylint: disable-next=consider-merging-classes-inherited
    _inherit = "project.task"

    git_merge_environment_ids = fields.Many2many(
        "project.agile.environment",
        compute="_compute_git_environment_evidence",
        search="_search_git_merge_environments",
        string="Merge observed in",
        compute_sudo=False,
    )
    git_environment_merge_count = fields.Integer(
        compute="_compute_git_environment_evidence",
        compute_sudo=False,
        string="Observed environment merges",
    )
    git_environment_evidence = fields.Html(
        compute="_compute_git_environment_evidence",
        compute_sudo=False,
        string="Historical Git merge evidence",
        sanitize=True,
    )
    git_uat_without_production_id = fields.Many2one(
        "project.agile.environment",
        compute="_compute_git_environment_evidence",
        search="_search_git_uat_without_production",
        compute_sudo=False,
        string="Merged into, not Production",
    )

    @api.model
    def _check_environment_derived_input(self, values):
        if any(
            key in values or f"default_{key}" in self.env.context
            for key in _EVIDENCE_FIELDS
        ):
            raise AccessError(self.env._("Git merge evidence is read-only."))
        return super()._check_environment_derived_input(values)

    @api.model
    def _git_evidence_task_domain(self):
        return [
            ("active", "=", True),
            ("project_id.active", "=", True),
            ("project_id.agile_enabled", "=", True),
            ("has_template_ancestor", "=", False),
            ("has_project_template", "=", False),
        ]

    @api.model
    def _git_visible_mappings(self, project_ids):
        return self.env["project.git.environment.branch"].search(
            [
                ("project_id", "in", project_ids),
                ("active", "=", True),
                ("environment_id.active", "=", True),
                ("repository_id.active", "=", True),
            ]
        )

    def _git_merge_evidence(self):
        """Join only visible exact association pairs in bulk, never a Cartesian join.

        Each result contains current visible mappings and known positives.
        Absence is deliberately not a code-presence assertion.
        """
        tasks = self.search(
            Domain.AND(
                [
                    Domain("id", "in", self.ids),
                    Domain(self._git_evidence_task_domain()),
                ]
            )
        )
        projects = self.env["project.project"].search(
            [
                ("id", "in", tasks.project_id.ids),
            ]
        )
        mappings = self._git_visible_mappings(projects.ids)
        by_repository = defaultdict(list)
        by_project = defaultdict(list)
        for mapping in mappings:
            by_repository[mapping.repository_id.id].append(mapping)
            by_project[mapping.project_id.id].append(mapping)
        associations = self.env["project.git.task.association"].search_fetch(
            [
                ("task_id", "in", tasks.ids),
                ("source_type", "=", "pull_request"),
                ("repository_id", "in", list(by_repository)),
            ],
            ["task_id", "repository_id", "source_provider_id"],
        )
        requests = self.env["project.git.pull.request"].search_fetch(
            [
                ("repository_id", "in", list(by_repository)),
                (
                    "provider_request_id",
                    "in",
                    associations.mapped("source_provider_id"),
                ),
            ],
            [
                "repository_id",
                "provider_request_id",
                "state",
                "target_branch",
                "merged_at",
                "ordering_state",
                "number",
            ],
        )
        by_pair = {(pr.repository_id.id, pr.provider_request_id): pr for pr in requests}
        result = {task.id: {"mappings": [], "positive": []} for task in self}
        for task in tasks:
            result[task.id]["mappings"] = by_project[task.project_id.id]
        for association in associations:
            pr = by_pair.get(
                (association.repository_id.id, association.source_provider_id)
            )
            if pr is None:
                continue
            for mapping in by_repository[association.repository_id.id]:
                # Repository moves retain old associations, not current ownership.
                if not (
                    association.task_id.project_id
                    == mapping.project_id
                    == mapping.repository_id.project_id
                ):
                    continue
                item = (mapping, pr)
                if self._git_is_observed_merge(mapping, pr):
                    result[association.task_id.id]["positive"].append(item)
        return result

    @api.model
    def _git_is_observed_merge(self, mapping, pr):
        """Single positive predicate, including known-only confidence."""
        return bool(
            pr.state == "merged"
            and pr.merged_at
            and pr.ordering_state == "known"
            and pr.target_branch == mapping.branch_name
        )

    @api.model
    def _git_evidence_html(self, evidence):
        if not evidence["mappings"]:
            return False
        by_environment = {
            mapping.environment_id: self.env["project.git.pull.request"]
            for mapping in evidence["mappings"]
        }
        for mapping, pr in evidence["positive"]:
            by_environment[mapping.environment_id] |= pr
        rows = []
        for environment, requests in by_environment.items():
            merges = [
                Markup("%s: PR %s")
                % (pr.repository_id.name, pr.number or pr.provider_request_id)
                for pr in requests.sorted(
                    key=lambda pr: (pr.repository_id.id, pr.provider_request_id)
                )
            ]
            summary = (
                Markup(self.env._("Merged in %s")) % Markup(", ").join(merges)
                if merges
                else self.env._("No merge seen")
            )
            rows.append(Markup("<li>%s: %s</li>") % (environment.name, summary))
        return Markup("<ul>%s</ul>") % Markup("").join(rows)

    # Membership explicitly requires active records, independent of active_test.
    # That cache-key special case only supports relational fields in Odoo 19.
    @api.depends_context("uid", "allowed_company_ids")
    @api.depends(
        "active",
        "has_template_ancestor",
        "has_project_template",
        "project_id.active",
        "project_id.agile_enabled",
        "project_id.git_environment_branch_ids",
        "project_id.git_environment_branch_ids.active",
        "project_id.git_environment_branch_ids.branch_name",
        "project_id.git_environment_branch_ids.environment_id.active",
        "project_id.git_environment_branch_ids.environment_id.is_production",
        "project_id.git_environment_branch_ids.repository_id.active",
        "git_association_ids",
        "git_association_ids.repository_id.git_pull_request_ids",
        "git_association_ids.repository_id.git_pull_request_ids.state",
        "git_association_ids.repository_id.git_pull_request_ids.merged_at",
        "git_association_ids.repository_id.git_pull_request_ids.target_branch",
        "git_association_ids.repository_id.git_pull_request_ids.ordering_state",
        "git_association_ids.repository_id.git_pull_request_ids.updated_at",
        "git_association_ids.repository_id.git_pull_request_ids.last_seen_at",
    )
    def _compute_git_environment_evidence(self):
        evidence = self._git_merge_evidence()
        for task in self:
            current = evidence[task.id]
            task.git_merge_environment_ids = self.env[
                "project.agile.environment"
            ].browse(
                sorted(
                    {mapping.environment_id.id for mapping, _pr in current["positive"]}
                )
            )
            task.git_environment_merge_count = len(current["positive"])
            task.git_environment_evidence = self._git_evidence_html(current)
            task.git_uat_without_production_id = False

    @api.model
    def _git_selected_environment_ids(self, operator, value):
        environments = self.env["project.agile.environment"]
        if operator in ("any", "not any"):
            return environments.search(value).ids
        if operator in ("in", "not in"):
            return environments.search([("id", "in", value)]).ids
        if operator in ("like", "ilike", "=like", "=ilike", "not like", "not ilike"):
            return environments.search(
                [("name", operator.removeprefix("not "), value)]
            ).ids
        return None

    @api.model
    def _git_environment_search(self, operator, value, gap=False):
        environment_ids = self._git_selected_environment_ids(operator, value)
        if environment_ids is None:
            return NotImplemented
        projects = (
            self.env["project.agile.environment"].browse(environment_ids).project_id
        )
        tasks = self.search(
            Domain(self._git_evidence_task_domain())
            & Domain("project_id", "in", projects.ids)
        )
        matches = []
        for task_id, evidence in tasks._git_merge_evidence().items():
            positive = {
                mapping.environment_id.id for mapping, _pr in evidence["positive"]
            }
            selected = positive.intersection(environment_ids)
            production = {
                mapping.environment_id.id
                for mapping in evidence["mappings"]
                if mapping.environment_id.is_production
            }
            if selected and (
                not gap or (production and not positive.intersection(production))
            ):
                matches.append(task_id)
        return Domain("id", "not in" if operator.startswith("not ") else "in", matches)

    @api.model
    def _search_git_merge_environments(self, operator, value):
        return self._git_environment_search(operator, value)

    @api.model
    def _search_git_uat_without_production(self, operator, value):
        return self._git_environment_search(operator, value, gap=True)

    def action_open_git_environment_merges(self):
        self.ensure_one()
        self.check_access("read")
        evidence = self._git_merge_evidence()[self.id]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "project_agile_git.action_project_git_pull_request"
        )
        action["domain"] = [
            ("id", "in", sorted({pr.id for _mapping, pr in evidence["positive"]}))
        ]
        return action

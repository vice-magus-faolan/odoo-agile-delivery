"""Bounded deterministic proposals: no Task writes, attempts, effects or scheduler."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .policy_authority import clean_context, lock_records, require_capability
from .policy_evidence import (
    MAX_BATCH, MAX_EVIDENCE, OUTCOMES, REASONS, VERSION, canonical, check_condition,
    fingerprint, pr_condition, reduce_conditions,
)
from .project_git_policy_observation import check_evidence, pr_evidence, timestamp


class ProjectGitPolicyEvaluation(models.Model):
    _name = "project.git.policy.evaluation"
    _inherit = "project.git.policy.task.scope"
    _description = "Git Policy Dry Run Decision"
    _check_company_auto = True
    _order = "id desc"

    repository_id = fields.Many2one("project.git.repository", required=True, readonly=True, ondelete="restrict", index=True)
    project_id = fields.Many2one("project.project", required=True, readonly=True, ondelete="restrict", index=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True, ondelete="restrict", index=True)
    task_id = fields.Many2one("project.task", required=True, readonly=True, ondelete="restrict", index=True)
    agile_key = fields.Char(required=True, readonly=True, index=True)
    pull_request_id = fields.Many2one("project.git.pull.request", required=True, readonly=True, ondelete="restrict", index=True)
    rule_id = fields.Many2one("project.git.policy.rule", required=True, readonly=True, ondelete="restrict", index=True)
    activation_id = fields.Many2one("project.git.policy.activation", readonly=True, ondelete="restrict", index=True)
    revision_id = fields.Many2one("project.git.policy.revision", readonly=True, ondelete="restrict", index=True)
    observation_ids = fields.Many2many("project.git.policy.observation", relation="project_git_policy_eval_observation_rel", readonly=True)
    mode = fields.Selection([("dry_run", "Dry Run (Never Executable)")], required=True, readonly=True)
    outcome = fields.Selection(OUTCOMES, required=True, readonly=True, index=True)
    reason = fields.Selection(REASONS, required=True, readonly=True, index=True)
    expected_stage_id = fields.Many2one("project.task.type", readonly=True, ondelete="restrict")
    expected_state = fields.Char(readonly=True)
    expected_write_date = fields.Datetime(readonly=True)
    snapshot_version = fields.Integer(required=True, readonly=True)
    snapshot_json = fields.Text(required=True, readonly=True)
    fingerprint = fields.Char(required=True, readonly=True, index=True)
    evaluated_at = fields.Datetime(required=True, readonly=True)

    _fingerprint_unique = models.Constraint("UNIQUE(fingerprint)", "This exact dry-run decision is already recorded.")

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(_("Only the bounded private evaluator can append a decision."))

    def write(self, values):
        raise ValidationError(_("Policy dry-run decisions are immutable."))

    def unlink(self):
        raise ValidationError(_("Policy decision history is retained."))

    @api.model
    def _load_batch(self, repository, after_id):
        """Fixed-model, current-user searches; no sudo existence/count oracle.

        Limits are hard bounds, not truncation-based winners. Overflow produces a
        fail-closed diagnostic instead of certifying a partially loaded candidate.
        """
        prs = self.env["project.git.pull.request"].search([
            ("repository_id", "=", repository.id), ("state", "=", "merged"), ("id", ">", after_id),
        ], order="id", limit=MAX_BATCH)
        rules = self.env["project.git.policy.rule"].with_context(active_test=False).search([
            ("repository_id", "=", repository.id),
        ], order="id", limit=MAX_BATCH + 1)
        activations = rules.activation_id
        names = activations.revision_id.required_check_ids.mapped("name")
        associations = self.env["project.git.task.association"].search([
            ("repository_id", "=", repository.id), ("source_type", "=", "pull_request"),
            ("source_provider_id", "in", prs.mapped("provider_request_id")),
        ], limit=MAX_BATCH * MAX_EVIDENCE + 1)
        audits = self.env["project.git.association.audit"].search([
            ("repository_id", "=", repository.id), ("delivery_id", "in", prs.provenance_delivery_id.ids),
            ("source_type", "=", "pull_request"),
        ], limit=MAX_BATCH * MAX_EVIDENCE * MAX_EVIDENCE + 1)
        checks = self.env["project.git.check"].search([
            ("repository_id", "=", repository.id), ("head_sha", "in", prs.mapped("head_sha")),
            ("name", "in", names),
        ], limit=MAX_BATCH * MAX_EVIDENCE + 1)
        # Native Task search filters hidden associations before any Task data enters
        # a proposal. Reading an association ID does not grant Task read authority.
        tasks = self.env["project.task"].with_context(active_test=False).search([
            ("id", "in", associations.task_id.ids), ("project_id", "=", repository.project_id.id),
            ("company_id", "=", repository.company_id.id),
        ])
        history = self.search([
            ("repository_id", "=", repository.id), ("pull_request_id", "in", prs.ids),
            ("task_id", "in", tasks.ids),
        ], order="id", limit=8001)
        overflow = any((
            len(rules) > MAX_BATCH, len(associations) > MAX_BATCH * MAX_EVIDENCE,
            len(audits) > MAX_BATCH * MAX_EVIDENCE * MAX_EVIDENCE,
            len(checks) > MAX_BATCH * MAX_EVIDENCE, len(history) > 8000,
        ))
        return prs, rules[:MAX_BATCH], associations, audits, checks, tasks, history, overflow

    @api.model
    def _check_names(self, pr, revision, checks, now):
        conditions, used = [], self.env["project.git.check"]
        for name in sorted(revision.required_check_ids.mapped("name")):
            matches = checks.filtered(lambda c: c.name == name and c.head_sha == pr.head_sha)
            if not matches:
                conditions.append(("waiting", "missing_check"))
            elif len(matches) != 1:
                conditions.append(("rejected", "ambiguous_check"))
                # More than one identity stays ambiguous; no numeric-ID ordering.
                used |= matches[:MAX_EVIDENCE]
            else:
                used |= matches
                try:
                    check_evidence(matches, pr.repository_id, now)
                    result = check_condition(matches, pr.merged_at, now)
                except (AccessError, ValidationError):
                    result = ("rejected", "invalid_provenance")
                if result:
                    conditions.append(result)
        if len(used) > MAX_EVIDENCE:
            return ("rejected", "evidence_limit"), self.env["project.git.check"]
        result = reduce_conditions(conditions)
        if result:
            return result, used
        return ("matched", "checks_passed" if revision.required_check_ids else "no_ci_condition"), used

    @api.model
    def _scope_condition(self, repository, rule, task):
        if not repository.active or not repository.project_id.active:
            return "skipped", "inactive_repository"
        if not task.active:
            return "skipped", "inactive_task"
        if not rule.active or not rule.activation_id or not repository.project_id.git_policy_enabled:
            return "skipped", "inactive_policy"
        return None

    @api.model
    def _initial_condition(self, repository, rule, task, prior, overflow):
        if overflow:
            return "rejected", "evidence_limit"
        result = self._scope_condition(repository, rule, task)
        if result:
            return result
        if prior and (prior.expected_stage_id != task.stage_id or prior.expected_state != task.state
                      or prior.expected_write_date != task.write_date):
            return "skipped", "stale_task"
        if task.stage_id == rule.activation_id.revision_id.target_stage_id:
            return "skipped", "already_target"
        if task.is_closed or task.stage_id not in rule.activation_id.revision_id.allowed_source_stage_ids:
            return "skipped", "ineligible_task"
        if "is_template" in task._fields and task.is_template:
            return "skipped", "ineligible_task"
        return None

    @api.model
    def _candidate(self, repository, rule, pr, task, associations, audits, checks, prior, overflow, authorized, now):
        result = self._initial_condition(repository, rule, task, prior, overflow)
        observation = self.env["project.git.policy.observation"]
        if result:
            return result, observation
        activation = rule.activation_id
        if not authorized:
            return ("rejected", "invalid_authority"), observation
        try:
            pr_evidence(pr, task, associations, audits, now)
        except (AccessError, ValidationError):
            return ("rejected", "invalid_provenance"), observation
        result = pr_condition(pr, activation, now)
        used = self.env["project.git.check"]
        if not result:
            result, used = self._check_names(pr, activation.revision_id, checks, now)
        try:
            observation = observation._seal(pr, task, associations, audits, used, now)
        except (AccessError, ValidationError):
            return ("rejected", "invalid_provenance"), observation.browse()
        return result, observation

    @api.model
    def _append(self, repository, rule, pr, task, prior, result, observation, conflicts, now):
        """Only material input/outcome changes append; polling never renews freshness."""
        activation = rule.activation_id
        expected = {
            "stage_id": prior.expected_stage_id.id if prior else task.stage_id.id,
            "state": prior.expected_state if prior else task.state,
            "write_date": timestamp(prior.expected_write_date if prior else task.write_date),
        }
        snapshot = {
            "version": VERSION, "mode": "dry_run", "repository_id": repository.id,
            "project_id": repository.project_id.id, "company_id": repository.company_id.id,
            "rule_id": rule.id, "activation_id": activation.id, "revision_id": activation.revision_id.id,
            "pull_request_id": pr.id, "task_id": task.id, "agile_key": task.agile_key,
            "expected_task": expected,
            "current_task": {"stage_id": task.stage_id.id, "state": task.state, "active": task.active,
                             "write_date": timestamp(task.write_date)},
            "outcome": result[0], "reason": result[1], "observation": observation.fingerprint if observation else False,
            "conflicting_rule_ids": sorted(conflicts),
        }
        digest = fingerprint(snapshot)
        existing = self.search([("fingerprint", "=", digest)], limit=1)
        if existing:
            return existing
        return super(ProjectGitPolicyEvaluation, self.sudo().with_context({})).create({
            "repository_id": repository.id, "project_id": repository.project_id.id,
            "company_id": repository.company_id.id, "task_id": task.id, "agile_key": task.agile_key,
            "pull_request_id": pr.id, "rule_id": rule.id, "activation_id": activation.id,
            "revision_id": activation.revision_id.id, "observation_ids": [(6, 0, observation.ids)],
            "mode": "dry_run", "outcome": result[0], "reason": result[1],
            "expected_stage_id": expected["stage_id"], "expected_state": expected["state"],
            "expected_write_date": prior.expected_write_date if prior else task.write_date, "snapshot_version": VERSION,
            "snapshot_json": canonical(snapshot), "fingerprint": digest, "evaluated_at": now,
        })

    @api.model
    def _authority_map(self, rules, tasks):
        """Batch concrete Task checks once per approval, not once per PR/Task/rule."""
        result = {}
        for rule in rules:
            try:
                if not rule.activation_id or not tasks:
                    result[rule.id] = False
                    continue
                # Nonmutating validation; dry-run never revokes control epochs.
                rule.activation_id._check_current_authority(tasks)
                result[rule.id] = True
            except (AccessError, ValidationError):
                result[rule.id] = False
        return result

    @api.model
    def _evaluate_repository(self, repository, after_id):
        """Serialize append-only dedupe on scoped control rows, never reserve an effect."""
        lock_records(repository.project_id)
        lock_records(repository)
        batch = self._load_batch(repository, after_id)
        prs, rules, associations, audits, checks, tasks, history, overflow = batch
        authorized = self._authority_map(rules, tasks)
        # Keep an initial fence per activation/PR/task; a later dry-run is not an
        # implicit retry of a manually changed Task. Apply adds its own real fence.
        prior = {}
        for item in history:
            prior.setdefault((item.activation_id.id, item.pull_request_id.id, item.task_id.id), item)
        now = fields.Datetime.now()
        decisions = self.browse()
        for pr in prs:
            associated = associations.filtered(lambda a: a.source_provider_id == pr.provider_request_id)
            scoped_tasks = tasks.filtered(lambda t: t.id in associated.task_id.ids)
            pr_overflow = overflow or len(scoped_tasks) > MAX_EVIDENCE
            for task in scoped_tasks.sorted("id")[:MAX_EVIDENCE]:
                candidates = []
                for rule in rules:
                    initial = prior.get((rule.activation_id.id, pr.id, task.id))
                    result, observation = self._candidate(repository, rule, pr, task, associated, audits, checks, initial, pr_overflow, authorized[rule.id], now)
                    candidates.append((rule, initial, result, observation))
                eligible = [r.id for r, _, result, _ in candidates if result[0] == "matched"]
                for rule, initial, result, observation in candidates:
                    conflicts = eligible if len(eligible) > 1 and rule.id in eligible else []
                    if conflicts:
                        result = ("conflicted", "conflicting_rules")
                    decisions |= self._append(repository, rule, pr, task, initial, result, observation, conflicts, now)
        return decisions, prs[-1].id if prs else after_id


class ProjectGitRepository(models.Model):
    _inherit = "project.git.repository"

    def action_dry_run_git_policy(self, after_id=0):
        """Explicit capability-owned twenty-PR page; never selects a Task or an action."""
        self.ensure_one()
        require_capability(self.env)
        if type(after_id) is not int or not 0 <= after_id <= 2147483647:
            raise ValidationError(_("Dry-run pagination requires a nonnegative integer cursor."))
        repository = self.with_context(clean_context(self.env))
        repository.check_access("read")
        repository.project_id.check_access("read")
        if not repository.company_id or repository.company_id not in repository.env.companies:
            raise AccessError(_("Dry-run requires a currently visible company-scoped repository."))
        decisions, next_pr_id = repository.env["project.git.policy.evaluation"]._evaluate_repository(repository, after_id)
        return {
            "type": "ir.actions.act_window", "name": _("Git Policy Dry Run"),
            "res_model": "project.git.policy.evaluation", "view_mode": "list,form",
            "domain": [("id", "in", decisions.ids)], "context": {},
            "next_pr_cursor": next_pr_id,
        }

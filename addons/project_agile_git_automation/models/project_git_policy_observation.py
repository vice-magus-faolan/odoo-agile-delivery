"""Seal bounded normalized values, not payload-selected targets or authentication flags."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

from .policy_authority import check_scope
from .policy_evidence import DIGEST, FULL_SHA, KEY, MAX_EVIDENCE, VERSION, canonical, fingerprint


class ProjectGitPolicyTaskScope(models.AbstractModel):
    """Live native Task visibility intersects Project/company rules on every surface."""
    _name = "project.git.policy.task.scope"
    _inherit = "project.git.policy.scope"
    _description = "Current Task Policy Visibility"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        if not self.env.su and not bypass_access:
            tasks = self.env["project.task"]._search([], active_test=False)
            domain = Domain(domain) & Domain("task_id", "in", tasks)
        return super()._search(domain, offset, limit, order, active_test=active_test, bypass_access=bypass_access)


def timestamp(value):
    return value.isoformat(sep=" ", timespec="microseconds") if value else False


def delivery_evidence(delivery, repository, events, now):
    """M6 protected ledger is trusted ingress, not post-retention independent HMAC proof.

    Trusted server code/database administration is the ADR-012 trust root. State
    alone is insufficient: receipt and settlement metadata and scope must agree.
    Ordinary users cannot mint/edit these rows; caller context is never consulted.
    """
    if len(delivery) != 1:
        raise ValidationError(repository.env._("Missing normalized policy receipt."))
    delivery.check_access("read")
    if delivery.repository_id != repository or delivery.company_id != repository.company_id:
        raise ValidationError(repository.env._("Invalid normalized policy provenance."))
    if delivery.event_type not in events or delivery.state != "processed":
        raise ValidationError(repository.env._("Invalid normalized policy provenance."))
    if delivery.lease_token or delivery.lease_expires_at or delivery.attempt_count < 1:
        raise ValidationError(repository.env._("Unsettled normalized policy provenance."))
    if not delivery.received_at or not delivery.processed_at or not delivery.received_at <= delivery.processed_at <= now:
        raise ValidationError(repository.env._("Invalid normalized policy settlement time."))
    if not DIGEST.fullmatch(delivery.payload_sha256 or "") or not 0 < delivery.payload_size <= 262144:
        raise ValidationError(repository.env._("Invalid normalized policy receipt."))
    return {
        "id": delivery.id, "digest": delivery.payload_sha256,
        "received_at": timestamp(delivery.received_at), "processed_at": timestamp(delivery.processed_at),
        "event_type": delivery.event_type,
    }


def association_matches(association, pr, task):
    return (association.task_id == task and association.agile_key == task.agile_key
            and association.source_provider_id == pr.provider_request_id
            and association.source_type == "pull_request" and association.repository_id == pr.repository_id)


def audit_matches(audit, pr, task):
    return (audit.task_id == task and audit.agile_key == task.agile_key
            and audit.delivery_id == pr.provenance_delivery_id
            and audit.repository_id == pr.repository_id and audit.source_type == "pull_request"
            and audit.source_provider_id == pr.provider_request_id
            and audit.outcome in {"associated", "already_associated"}
            and audit.reason in {"exact_key", "duplicate"}
            and audit.source_field in {"title", "body", "head_ref"})


def validate_pr_identity(pr, task):
    """Current local identity/scope, not provider text or a caller-selected ID."""
    repository = pr.repository_id
    if pr.state != "merged" or not FULL_SHA.fullmatch(pr.head_sha or ""):
        raise ValidationError(repository.env._("Invalid normalized merged PR evidence."))
    if task.project_id != repository.project_id or task.company_id != repository.company_id:
        raise ValidationError(repository.env._("Policy associations must retain their original scope."))
    if not KEY.fullmatch(task.agile_key or "") or not 1 <= len(pr.provider_request_id) <= 128:
        raise ValidationError(repository.env._("Invalid immutable policy identity."))
    if not 1 <= len(task.agile_key) <= 64 or not pr.target_branch or len(pr.target_branch) > 255:
        raise ValidationError(repository.env._("Policy source identities must stay bounded."))
    if not task.active:
        raise ValidationError(repository.env._("Policy observations require an active Task."))


def pr_evidence(pr, task, associations, audits, now):
    """Only the current PR delivery's exact-key audit can validate a persisted link."""
    pr.check_access("read")
    task.check_access("read")
    validate_pr_identity(pr, task)
    repository = pr.repository_id
    delivery = delivery_evidence(pr.provenance_delivery_id, repository, {"pull_request"}, now)
    matches = associations.filtered(lambda a: association_matches(a, pr, task))
    proofs = audits.filtered(lambda a: audit_matches(a, pr, task))
    if len(matches) != 1 or not proofs or len(proofs) > MAX_EVIDENCE:
        raise ValidationError(repository.env._("Current-delivery immutable key evidence is required."))
    return {
        "id": pr.id, "provider_request_id": pr.provider_request_id, "head_sha": pr.head_sha,
        "target_branch": pr.target_branch, "merged_at": timestamp(pr.merged_at),
        "updated_at": timestamp(pr.updated_at), "ordering_state": pr.ordering_state,
        "delivery": delivery, "association_id": matches.id, "audit_ids": sorted(proofs.ids),
    }


def check_evidence(check, repository, now):
    check.check_access("read")
    if check.repository_id != repository or not FULL_SHA.fullmatch(check.head_sha or ""):
        raise ValidationError(repository.env._("Invalid normalized check evidence."))
    if not 1 <= len(check.provider_check_id) <= 128 or not 1 <= len(check.name) <= 255:
        raise ValidationError(repository.env._("Invalid normalized check identity."))
    return {
        "id": check.id, "provider_check_id": check.provider_check_id, "name": check.name,
        "head_sha": check.head_sha, "state": check.state, "ordering_state": check.ordering_state,
        "updated_at": timestamp(check.updated_at), "completed_at": timestamp(check.completed_at),
        "delivery": delivery_evidence(check.provenance_delivery_id, repository, {"check_run", "check_suite"}, now),
    }


class ProjectGitPolicyObservation(models.Model):
    """One immutable PR/Task evidence bundle with at most twenty exact check references."""
    _name = "project.git.policy.observation"
    _inherit = "project.git.policy.task.scope"
    _description = "Sealed Git Policy Observation"
    _check_company_auto = True
    _order = "id desc"

    repository_id = fields.Many2one("project.git.repository", required=True, readonly=True, ondelete="restrict", index=True)
    project_id = fields.Many2one("project.project", required=True, readonly=True, ondelete="restrict", index=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True, ondelete="restrict", index=True)
    task_id = fields.Many2one("project.task", required=True, readonly=True, ondelete="restrict", index=True)
    agile_key = fields.Char(required=True, readonly=True)
    provider_request_id = fields.Char(required=True, readonly=True, index=True)
    snapshot_version = fields.Integer(required=True, readonly=True)
    snapshot_json = fields.Text(required=True, readonly=True)
    fingerprint = fields.Char(required=True, readonly=True, index=True)
    observed_at = fields.Datetime(required=True, readonly=True)

    _fingerprint_unique = models.Constraint("UNIQUE(fingerprint)", "This exact policy observation is already sealed.")

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(_("Only the validated private observation producer can mint a seal."))

    def write(self, values):
        raise ValidationError(_("Policy observations are immutable."))

    def unlink(self):
        raise ValidationError(_("Policy evidence is retained."))

    @api.model
    def _seal(self, pr, task, associations, audits, checks, now):
        """Re-resolve all supplied ORM records; arguments/context cannot supply a snapshot."""
        pr = self.env["project.git.pull.request"].browse(pr.ids)
        task = self.env["project.task"].browse(task.ids)
        associations = self.env["project.git.task.association"].browse(associations.ids)
        audits = self.env["project.git.association.audit"].browse(audits.ids)
        checks = self.env["project.git.check"].browse(checks.ids)
        associations.check_access("read")
        audits.check_access("read")
        checks.check_access("read")
        repository = pr.repository_id
        check_scope(repository, operation="read")
        evidence = pr_evidence(pr, task, associations, audits, now)
        if len(checks) > MAX_EVIDENCE:
            raise ValidationError(_("Check evidence is bounded to twenty references."))
        if any(check.head_sha != pr.head_sha for check in checks):
            raise ValidationError(_("Check evidence must retain the exact PR head SHA."))
        check_rows = [check_evidence(c, repository, now) for c in checks.sorted("provider_check_id")]
        snapshot = {
            "version": VERSION, "repository_id": repository.id, "project_id": repository.project_id.id,
            "company_id": repository.company_id.id, "task_id": task.id, "agile_key": task.agile_key,
            "pr": evidence, "checks": check_rows,
        }
        digest = fingerprint(snapshot)
        if len(canonical(snapshot)) > 65536:
            raise ValidationError(_("Policy observation snapshots must stay bounded."))
        existing = self.search([("fingerprint", "=", digest)], limit=1)
        if existing:
            return existing
        return super(ProjectGitPolicyObservation, self.sudo().with_context({})).create({
            "repository_id": repository.id, "project_id": repository.project_id.id,
            "company_id": repository.company_id.id, "task_id": task.id, "agile_key": task.agile_key,
            "provider_request_id": pr.provider_request_id, "snapshot_version": VERSION,
            "snapshot_json": canonical(snapshot), "fingerprint": digest, "observed_at": now,
        })
